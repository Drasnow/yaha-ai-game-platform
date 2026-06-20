import { NextResponse } from "next/server";
import { z } from "zod";

import { createSession, hashPassword } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

const registerSchema = z.object({
  email: z.email().trim().toLowerCase(),
  password: z.string().min(8, "Password must be at least 8 characters"),
  displayName: z.string().trim().min(1).max(60).optional(),
});

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const parsed = registerSchema.safeParse(body);

  if (!parsed.success) {
    return NextResponse.json(
      { error: "Invalid request", details: parsed.error.flatten() },
      { status: 400 },
    );
  }

  const { email, password, displayName } = parsed.data;
  const existingUser = await prisma.user.findUnique({ where: { email } });

  if (existingUser) {
    return NextResponse.json({ error: "Email already registered" }, { status: 409 });
  }

  const user = await prisma.user.create({
    data: {
      email,
      passwordHash: await hashPassword(password),
      displayName: displayName ?? email.split("@")[0],
    },
    select: {
      id: true,
      email: true,
      displayName: true,
      avatarUrl: true,
    },
  });

  await createSession(user.id);

  return NextResponse.json({ user }, { status: 201 });
}
