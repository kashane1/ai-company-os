// push_dispatcher
//
// Drains rows from public.push_outbox where status = 'pending' and
// next_attempt_at <= now(), signs an APNs JWT (ES256, .p8 token-based
// auth — cert-based is legacy), and POSTs to
// https://api.push.apple.com/3/device/{token}.
//
// Deployment requires three Edge Function secrets:
//   - APNS_AUTH_KEY_P8: contents of the AuthKey_*.p8 file (PEM, multi-line OK).
//   - APNS_KEY_ID: the 10-char key id from Apple Developer.
//   - APNS_TEAM_ID: the 10-char Apple team id.
// These are NOT included in source. To deploy:
//   supabase secrets set APNS_AUTH_KEY_P8="$(cat AuthKey_XXXX.p8)" \
//                        APNS_KEY_ID=XXXXXXXXXX \
//                        APNS_TEAM_ID=YYYYYYYYYY
//   supabase functions deploy push_dispatcher
//
// The function is invoked on a 30s pg_cron schedule (or via pg_net
// http_post from a trigger). It batches up to 50 outbox rows per
// invocation; idempotency is enforced by the apns-id header which
// matches push_outbox.apns_id.

import { createClient } from "npm:@supabase/supabase-js@2";
import { create as createJWT, getNumericDate } from "https://deno.land/x/djwt@v3.0.2/mod.ts";

const APNS_TOPIC = "io.aicompanyos.products.afterplans";
const APNS_HOST = "https://api.push.apple.com";
const BATCH_LIMIT = 50;
const MAX_ATTEMPTS = 5;

interface OutboxRow {
    id: string;
    recipient_id: string;
    apns_id: string;
    event_type: string;
    payload: Record<string, unknown>;
    attempts: number;
}

interface DeviceRow {
    token: string;
    user_id: string;
    platform: string;
}

let cachedJWT: { token: string; expiresAt: number } | null = null;

async function apnsToken(): Promise<string> {
    const now = Math.floor(Date.now() / 1000);
    if (cachedJWT && cachedJWT.expiresAt > now + 60) {
        return cachedJWT.token;
    }
    const keyP8 = Deno.env.get("APNS_AUTH_KEY_P8") ?? "";
    const keyId = Deno.env.get("APNS_KEY_ID") ?? "";
    const teamId = Deno.env.get("APNS_TEAM_ID") ?? "";
    if (!keyP8 || !keyId || !teamId) {
        throw new Error("APNs secrets missing — set APNS_AUTH_KEY_P8, APNS_KEY_ID, APNS_TEAM_ID");
    }
    // PEM → CryptoKey
    const pemBody = keyP8.replace(/-----[^-]+-----/g, "").replace(/\s+/g, "");
    const der = Uint8Array.from(atob(pemBody), c => c.charCodeAt(0));
    const cryptoKey = await crypto.subtle.importKey(
        "pkcs8",
        der.buffer,
        { name: "ECDSA", namedCurve: "P-256" },
        false,
        ["sign"],
    );
    const jwt = await createJWT(
        { alg: "ES256", kid: keyId, typ: "JWT" },
        { iss: teamId, iat: getNumericDate(0) },
        cryptoKey,
    );
    cachedJWT = { token: jwt, expiresAt: now + 50 * 60 };
    return jwt;
}

async function dispatchOne(row: OutboxRow, devices: DeviceRow[], jwt: string) {
    const body = JSON.stringify({
        aps: {
            alert: {
                title: titleFor(row),
                body: bodyFor(row),
            },
            sound: "default",
        },
        event: row.event_type,
        ...row.payload,
    });

    let lastStatus = 0;
    let lastErr: string | undefined;
    for (const device of devices) {
        const url = `${APNS_HOST}/3/device/${device.token}`;
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "authorization": `bearer ${jwt}`,
                "apns-topic": APNS_TOPIC,
                "apns-id": row.apns_id,
                "apns-push-type": "alert",
                "content-type": "application/json",
            },
            body,
        });
        lastStatus = response.status;
        if (!response.ok) {
            lastErr = await response.text();
        }
    }
    return { ok: lastStatus === 200, error: lastErr };
}

function titleFor(row: OutboxRow): string {
    switch (row.event_type) {
        case "plan_join": return "Someone joined your plan.";
        case "plan_confirmed": return "Your plan is locked.";
        case "context_formed": return "A new context just spawned around you.";
        case "post_wrap_recommendation": return "There's a follow-up worth knowing about.";
        default: return "After Plans";
    }
}

function bodyFor(row: OutboxRow): string {
    const title = (row.payload as { plan_title?: string }).plan_title ?? "your plan";
    return `${title}`;
}

Deno.serve(async () => {
    const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
    const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
    const sb = createClient(supabaseUrl, supabaseKey);

    const { data: pending, error } = await sb
        .from("push_outbox")
        .select("id, recipient_id, apns_id, event_type, payload, attempts")
        .eq("status", "pending")
        .lte("next_attempt_at", new Date().toISOString())
        .order("created_at", { ascending: true })
        .limit(BATCH_LIMIT);
    if (error) {
        return new Response(JSON.stringify({ error: error.message }), { status: 500 });
    }
    if (!pending || pending.length === 0) {
        return new Response(JSON.stringify({ processed: 0 }), { status: 200 });
    }

    const jwt = await apnsToken();
    const recipientIds = [...new Set(pending.map((p) => p.recipient_id))];
    const { data: devices } = await sb
        .from("push_devices")
        .select("token, user_id, platform")
        .in("user_id", recipientIds);

    const devicesByUser = new Map<string, DeviceRow[]>();
    for (const d of devices ?? []) {
        const arr = devicesByUser.get(d.user_id) ?? [];
        arr.push(d);
        devicesByUser.set(d.user_id, arr);
    }

    let sent = 0;
    let failed = 0;
    for (const row of pending) {
        const myDevices = devicesByUser.get(row.recipient_id) ?? [];
        if (myDevices.length === 0) {
            await sb.from("push_outbox").update({ status: "expired", updated_at: new Date().toISOString() }).eq("id", row.id);
            continue;
        }
        const result = await dispatchOne(row, myDevices, jwt);
        if (result.ok) {
            await sb.from("push_outbox").update({
                status: "sent", attempts: row.attempts + 1, updated_at: new Date().toISOString(),
            }).eq("id", row.id);
            sent++;
        } else {
            const next = row.attempts + 1;
            const status = next >= MAX_ATTEMPTS ? "failed" : "pending";
            const backoffSec = Math.pow(2, next) * 30;
            await sb.from("push_outbox").update({
                status, attempts: next, last_error: result.error,
                next_attempt_at: new Date(Date.now() + backoffSec * 1000).toISOString(),
                updated_at: new Date().toISOString(),
            }).eq("id", row.id);
            failed++;
        }
    }

    return new Response(JSON.stringify({ processed: pending.length, sent, failed }), { status: 200 });
});
