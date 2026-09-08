import { NextResponse, type NextRequest } from "next/server";

const TOKEN_KEY = "gsr_token";
const AUTH_PAGES = new Set(["/login", "/register"]);

export function middleware(request: NextRequest) {
  const token = request.cookies.get(TOKEN_KEY)?.value;
  if (token && AUTH_PAGES.has(request.nextUrl.pathname)) {
    const url = request.nextUrl.clone();
    url.pathname = "/research";
    url.search = "";
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/login", "/register"],
};
