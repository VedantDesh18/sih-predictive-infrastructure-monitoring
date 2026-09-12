import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(
  request: Request,
  context: RouteContext<"/api/v1/[...path]">
) {
  const { path } = await context.params;
  const incoming = new URL(request.url);
  const apiBase =
    process.env.INTERNAL_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000";
  try {
    const response = await fetch(
      `${apiBase}/api/v1/${path.join("/")}${incoming.search}`,
      { cache: "no-store" }
    );
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json(
      {
        error: {
          code: "API_UNAVAILABLE",
          message: "The monitoring API is unavailable.",
        },
      },
      { status: 503 }
    );
  }
}
