import { runScan } from "@/lib/sentinel";

export const dynamic = "force-dynamic";

// A read-only, fixed-command scan: no input is taken from the request.
export async function POST() {
  try {
    return Response.json(await runScan());
  } catch (e) {
    return Response.json({ error: `Sentinel scan failed: ${(e as Error).message}` }, { status: 500 });
  }
}
