"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, register } from "@/lib/api-client";
import { useAuthStore } from "@/lib/stores";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";

export default function LoginPage() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);

  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      let result;
      if (isRegister) {
        result = await register(email, username, password);
      } else {
        result = await login(email, password);
      }
      let userId = "";
try { const p = JSON.parse(atob(result.access_token.split(".")[1])); userId = p.sub || ""; } catch { /* ok */ }
if (result.refresh_token) { localStorage.setItem("refreshToken", result.refresh_token); }
setAuth(result.access_token, { id: userId, email, username: username || email, is_active: true });
      router.push("/chat");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Authentication failed";
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-100 to-slate-200">
      <Card className="w-full max-w-[400px] mx-4 shadow-lg">
        <div className="flex flex-col space-y-1.5 p-6 text-center">
          <div className="mx-auto mb-3 w-12 h-12 rounded-xl bg-blue-500 flex items-center justify-center">
            <span className="text-white font-bold text-lg">AI</span>
          </div>
          <h3 className="text-2xl font-semibold leading-none tracking-tight">
            {isRegister ? "Create Account" : "Welcome Back"}
          </h3>
          <p className="text-sm text-muted-foreground">
            {isRegister ? "Register for AI Workspace" : "Sign in to AI Workspace"}
          </p>
        </div>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium">Email</label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                required
                className="mt-1"
              />
            </div>
            {isRegister && (
              <div>
                <label className="text-sm font-medium">Username</label>
                <Input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="username"
                  required
                  className="mt-1"
                />
              </div>
            )}
            <div>
              <label className="text-sm font-medium">Password</label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="mt-1"
              />
            </div>
            {error && (
              <p className="text-sm text-red-500 bg-red-50 px-3 py-2 rounded">{error}</p>
            )}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Please wait..." : isRegister ? "Create Account" : "Sign In"}
            </Button>
          </form>
          <p className="text-sm text-center mt-4 text-muted-foreground">
            {isRegister ? "Already have an account?" : "Don't have an account?"}{" "}
            <button
              type="button"
              onClick={() => { setIsRegister(!isRegister); setError(""); }}
              className="text-blue-600 hover:underline font-medium"
            >
              {isRegister ? "Sign In" : "Register"}
            </button>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
