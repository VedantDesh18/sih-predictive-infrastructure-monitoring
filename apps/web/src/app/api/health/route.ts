import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const apiUrl =
    process.env.INTERNAL_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000";

  try {
    const res = await fetch(`${apiUrl}/api/v1/health`, {
      cache: "no-store",
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json(
      {
        status: "unhealthy",
        service: "paimana-ai-api",
        version: "unknown",
        dependencies: {
          database: "unhealthy",
        },
      },
      { status: 503 }
    );
  }
}
