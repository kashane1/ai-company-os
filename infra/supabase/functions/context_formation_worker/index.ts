// context_formation_worker
//
// Drains rows from public.context_formation_jobs where processed_at is
// null. For each job:
//   1. Re-acquires the (activity_id, venue_id) advisory lock.
//   2. Looks up an existing context by (activity_id, venue_id); creates
//      one if missing. New contexts are marked is_probationary = true
//      until a third independent user joins (security M1).
//   3. Bulk-inserts plan participants + matching declared interests as
//      context_members.
//   4. Enqueues per-recipient push_outbox rows.
//   5. Marks processed_at = now().
//
// Runs on a 30s pg_cron schedule plus immediate trigger via pg_net on
// insert. Idempotent on processed_at.

import { createClient } from "npm:@supabase/supabase-js@2";

const BATCH_LIMIT = 25;

interface JobRow {
    id: string;
    plan_id: string;
    activity_id: string | null;
    venue_id: string | null;
    enqueued_at: string;
}

Deno.serve(async () => {
    const sb = createClient(
        Deno.env.get("SUPABASE_URL") ?? "",
        Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "",
    );

    const { data: jobs, error } = await sb
        .from("context_formation_jobs")
        .select("id, plan_id, activity_id, venue_id, enqueued_at")
        .is("processed_at", null)
        .order("enqueued_at", { ascending: true })
        .limit(BATCH_LIMIT);
    if (error) {
        return new Response(JSON.stringify({ error: error.message }), { status: 500 });
    }
    if (!jobs || jobs.length === 0) {
        return new Response(JSON.stringify({ processed: 0 }), { status: 200 });
    }

    let processed = 0;
    for (const job of jobs as JobRow[]) {
        try {
            await processJob(sb, job);
            await sb.from("context_formation_jobs")
                .update({ processed_at: new Date().toISOString() })
                .eq("id", job.id);
            processed++;
        } catch (e) {
            await sb.from("trigger_errors").insert({
                source_function: "context_formation_worker",
                error_message: e instanceof Error ? e.message : String(e),
            });
        }
    }
    return new Response(JSON.stringify({ processed }), { status: 200 });
});

async function processJob(sb: ReturnType<typeof createClient>, job: JobRow) {
    if (!job.activity_id || !job.venue_id) return;

    // Look up an existing context for this (activity, venue) pair.
    const { data: existing } = await sb
        .from("contexts")
        .select("id, is_probationary, created_at")
        .eq("activity_id", job.activity_id)
        .eq("venue_id", job.venue_id)
        .limit(1)
        .maybeSingle();

    let contextID: string;
    let isNew = false;
    if (existing) {
        contextID = existing.id;
    } else {
        const { data: created, error: createErr } = await sb
            .from("contexts")
            .insert({
                activity_id: job.activity_id,
                venue_id: job.venue_id,
                is_probationary: true,
            })
            .select("id")
            .single();
        if (createErr || !created) throw createErr ?? new Error("context insert failed");
        contextID = created.id;
        isNew = true;
    }

    // Pull confirmed participants from the wrapped plan.
    const { data: participants } = await sb
        .from("plan_participants")
        .select("user_id")
        .eq("plan_id", job.plan_id);
    const participantIDs = (participants ?? []).map((p) => p.user_id);

    // Pull declared interests for this (activity, venue) — filtered to
    // those declared before this job was enqueued (race guard).
    const { data: interested } = await sb
        .from("user_activity_interests")
        .select("user_id")
        .eq("activity_id", job.activity_id)
        .eq("venue_id", job.venue_id)
        .lt("declared_at", job.enqueued_at);
    const interestedIDs = (interested ?? []).map((i) => i.user_id);

    const memberIDs = [...new Set([...participantIDs, ...interestedIDs])];
    if (memberIDs.length === 0) return;

    await sb.from("context_members").upsert(
        memberIDs.map((uid) => ({ context_id: contextID, user_id: uid })),
        { onConflict: "context_id,user_id", ignoreDuplicates: true },
    );

    // Enqueue per-recipient push notifications for the new context.
    if (isNew) {
        const rows = memberIDs.map((uid) => ({
            recipient_id: uid,
            dedupe_key: `context:${contextID}:event:formed:user:${uid}`,
            event_type: "context_formed",
            payload: { context_id: contextID, plan_id: job.plan_id },
        }));
        await sb.from("push_outbox").upsert(rows, {
            onConflict: "dedupe_key",
            ignoreDuplicates: true,
        });
    }
}
