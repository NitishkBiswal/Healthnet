"use client";

export type UserRole = "patient" | "provider" | "admin" | "auditor";

export const ROLE_CONFIG: Record<
  UserRole,
  { label: string; description: string; portal: string }
> = {
  patient: {
    label: "Patient",
    description: "Get your Health ID and manage your personal health permissions.",
    portal: "/patient",
  },
  provider: {
    label: "Doctor",
    description: "Access authorized patient records and clinical workflows.",
    portal: "/doctor",
  },
  admin: {
    label: "Administrator",
    description: "Manage trusted organizations, repositories and system controls.",
    portal: "/admin",
  },
  auditor: {
    label: "Auditor",
    description: "Review identity decisions, audit trails and system integrity.",
    portal: "/auditor",
  },
};

const KEYCLOAK_URL =
  process.env.NEXT_PUBLIC_KEYCLOAK_URL ?? "http://localhost:8180";
const REALM = process.env.NEXT_PUBLIC_KEYCLOAK_REALM ?? "healthnet";
const CLIENT_ID =
  process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID ?? "healthnet-frontend";

const K = {
  access: "healthnet_access_token",
  id: "healthnet_id_token",
  refresh: "healthnet_refresh_token",
  expires: "healthnet_expires_at",
  state: "healthnet_pkce_state",
  verifier: "healthnet_pkce_verifier",
  role: "healthnet_login_role",
} as const;

function base64Url(bytes: Uint8Array): string {
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function decodeJwtPayload(token: string): Record<string, unknown> {
  const part = token.split(".")[1];
  if (!part) throw new Error("Invalid access token");
  const normalized = part.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);
  return JSON.parse(atob(padded)) as Record<string, unknown>;
}

async function randomString(length = 32): Promise<string> {
  const bytes = new Uint8Array(length);
  crypto.getRandomValues(bytes);
  return base64Url(bytes);
}

async function challenge(verifier: string): Promise<string> {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(verifier),
  );
  return base64Url(new Uint8Array(digest));
}

export async function beginRegistration(): Promise<void> {
  const state = await randomString(32);
  const verifier = await randomString(64);
  const codeChallenge = await challenge(verifier);

  sessionStorage.setItem(K.state, state);
  sessionStorage.setItem(K.verifier, verifier);
  sessionStorage.setItem(K.role, "patient");

  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    redirect_uri: window.location.origin + "/auth/callback",
    response_type: "code",
    scope: "openid profile email",
    state,
    code_challenge: codeChallenge,
    code_challenge_method: "S256",
  });

  window.location.assign(
    KEYCLOAK_URL +
      "/realms/" +
      REALM +
      "/protocol/openid-connect/registrations?" +
      params.toString(),
  );
}

export async function beginLogin(role: UserRole): Promise<void> {
  const state = await randomString(32);
  const verifier = await randomString(64);
  const codeChallenge = await challenge(verifier);

  sessionStorage.setItem(K.state, state);
  sessionStorage.setItem(K.verifier, verifier);
  sessionStorage.setItem(K.role, role);

  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    redirect_uri: window.location.origin + "/auth/callback",
    response_type: "code",
    scope: "openid profile email",
    state,
    code_challenge: codeChallenge,
    code_challenge_method: "S256",
  });

  window.location.assign(
    KEYCLOAK_URL +
      "/realms/" +
      REALM +
      "/protocol/openid-connect/auth?" +
      params.toString(),
  );
}

export async function completeLogin(code: string, state: string): Promise<UserRole> {
  const existingRole = getSessionRole();
  if (existingRole && !sessionStorage.getItem(K.state)) {
    return existingRole;
  }

  const expectedState = sessionStorage.getItem(K.state);
  const verifier = sessionStorage.getItem(K.verifier);
  const expectedRole = sessionStorage.getItem(K.role) as UserRole | null;

  if (!expectedState || !verifier || !expectedRole || state !== expectedState) {
    throw new Error("Invalid authentication state. Please start login again.");
  }

  const body = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: CLIENT_ID,
    code,
    redirect_uri: window.location.origin + "/auth/callback",
    code_verifier: verifier,
  });

  const response = await fetch(
    KEYCLOAK_URL +
      "/realms/" +
      REALM +
      "/protocol/openid-connect/token",
    {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    },
  );

  if (!response.ok) {
    throw new Error("Keycloak could not complete the login.");
  }

  const token = (await response.json()) as {
    access_token: string;
    id_token?: string;
    refresh_token?: string;
    expires_in?: number;
  };

  const payload = decodeJwtPayload(token.access_token);
  const rawRoles =
    (payload.realm_access as { roles?: unknown[] } | undefined)?.roles ?? [];
  const roles = rawRoles
    .filter((role): role is string => typeof role === "string")
    .map((role) => role.toLowerCase());

  if (!roles.includes(expectedRole)) {
    clearSession();
    throw new Error(
      "This account is not authorized for the " +
        ROLE_CONFIG[expectedRole].label +
        " portal.",
    );
  }

  sessionStorage.setItem(K.access, token.access_token);
  if (token.id_token) sessionStorage.setItem(K.id, token.id_token);
  if (token.refresh_token) sessionStorage.setItem(K.refresh, token.refresh_token);
  sessionStorage.setItem(
    K.expires,
    String(Date.now() + (token.expires_in ?? 300) * 1000),
  );
  sessionStorage.removeItem(K.state);
  sessionStorage.removeItem(K.verifier);
  sessionStorage.setItem(K.role, expectedRole);
  return expectedRole;
}

export function getAccessToken(): string | null {
  return typeof window === "undefined"
    ? null
    : sessionStorage.getItem(K.access);
}

export function getSessionRole(): UserRole | null {
  if (typeof window === "undefined") return null;
  const token = getAccessToken();
  if (!token) return null;

  const selectedRole = sessionStorage.getItem(K.role) as UserRole | null;
  if (selectedRole && ROLE_CONFIG[selectedRole]) return selectedRole;

  try {
    const payload = decodeJwtPayload(token);
    const roles =
      ((payload.realm_access as { roles?: unknown[] } | undefined)?.roles ?? [])
        .filter((role): role is string => typeof role === "string")
        .map((role) => role.toLowerCase());

    if (roles.includes("provider")) return "provider";
    if (roles.includes("patient")) return "patient";
    if (roles.includes("admin")) return "admin";
    if (roles.includes("auditor")) return "auditor";
  } catch {
    return null;
  }
  return null;
}

export function getUserClaims(): {
  name?: string;
  email?: string;
  subject?: string;
} {
  const token = getAccessToken();
  if (!token) return {};

  try {
    const payload = decodeJwtPayload(token);
    return {
      name: typeof payload.name === "string" ? payload.name : undefined,
      email: typeof payload.email === "string" ? payload.email : undefined,
      subject: typeof payload.sub === "string" ? payload.sub : undefined,
    };
  } catch {
    return {};
  }
}

export function clearSession(): void {
  if (typeof window === "undefined") return;
  Object.values(K).forEach((key) => sessionStorage.removeItem(key));
}

export function logout(): void {
  const idToken =
    typeof window !== "undefined" ? sessionStorage.getItem(K.id) : null;
  clearSession();

  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    post_logout_redirect_uri: window.location.origin + "/",
  });
  if (idToken) params.set("id_token_hint", idToken);

  window.location.assign(
    KEYCLOAK_URL +
      "/realms/" +
      REALM +
      "/protocol/openid-connect/logout?" +
      params.toString(),
  );
}
