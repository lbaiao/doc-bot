import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";

import { Button } from "@/components/ui/button";
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/store/auth-store";
import { apiClient } from "@/lib/api-client";
import { AuthLayout } from "./AuthLayout";
import { Card, CardContent, CardFooter } from "@/components/ui/card";

const formSchema = z.object({
    email: z.string().email(),
    password: z.string().min(1, "Password is required"),
});

export function LoginForm() {
    const navigate = useNavigate();
    const setAuth = useAuthStore((state) => state.setAuth);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            email: "",
            password: "",
        },
    });

    async function onSubmit(values: z.infer<typeof formSchema>) {
        setLoading(true);
        setError(null);
        try {
            // 1. Login to get token
            const formData = new FormData();
            formData.append("username", values.email);
            formData.append("password", values.password);

            const loginRes = await apiClient.post("/v1/auth/jwt/login", formData, {
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
            });
            const token = loginRes.data.access_token;

            // 2. Get user details (optional, but good for store)
            // Since generic backend doesn't always return user on login, we might need to fetch /users/me
            // But for now, let's assume valid token means we can proceed. 
            // We'll mock the user object or fetch it if endpoints exist. 
            // Based on specs, we can try GET /v1/users/me (standard fastapi-users)

            // Temporarily set token first to allow common fetch
            useAuthStore.getState().setAuth(token, { id: "temp", email: values.email } as any);

            // Try fetching real user
            try {
                const userRes = await apiClient.get("/v1/users/me");
                setAuth(token, userRes.data);
            } catch (e) {
                // If fails, keep temp user
                console.warn("Could not fetch user details", e);
            }

            navigate("/app/home");
        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.detail || "Invalid email or password");
        } finally {
            setLoading(false);
        }
    }

    return (
        <AuthLayout title="Welcome back" subtitle="Login to your account">
            <Card>
                <CardContent className="pt-6">
                    <Form {...form}>
                        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                            <FormField
                                control={form.control}
                                name="email"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Email</FormLabel>
                                        <FormControl>
                                            <Input placeholder="name@example.com" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <FormField
                                control={form.control}
                                name="password"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Password</FormLabel>
                                        <FormControl>
                                            <Input type="password" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            {error && <div className="text-sm text-red-500">{error}</div>}
                            <Button type="submit" className="w-full" disabled={loading}>
                                {loading ? "Logging in..." : "Login"}
                            </Button>
                        </form>
                    </Form>
                </CardContent>
                <CardFooter className="justify-center">
                    <p className="text-sm text-muted-foreground">
                        Don't have an account?{" "}
                        <Link to="/signup" className="underline hover:text-primary">
                            Sign up
                        </Link>
                    </p>
                </CardFooter>
            </Card>
        </AuthLayout>
    );
}
