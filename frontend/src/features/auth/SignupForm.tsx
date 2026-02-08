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
import { apiClient } from "@/lib/api-client";
import { AuthLayout } from "./AuthLayout";
import { Card, CardContent, CardFooter } from "@/components/ui/card";

const formSchema = z.object({
    email: z.string().email(),
    password: z.string().min(8, "Password must be at least 8 characters"),
});

export function SignupForm() {
    const navigate = useNavigate();
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
            await apiClient.post("/v1/auth/register", values);
            navigate("/login");
        } catch (err: any) {
            console.error(err);
            if (err.response?.status === 400 && err.response?.data?.detail === "REGISTER_USER_ALREADY_EXISTS") {
                setError("User with this email already exists");
            } else {
                setError(err.response?.data?.detail || "Registration failed");
            }
        } finally {
            setLoading(false);
        }
    }

    return (
        <AuthLayout title="Create an account" subtitle="Enter your email to get started">
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
                                {loading ? "Creating account..." : "Sign Up"}
                            </Button>
                        </form>
                    </Form>
                </CardContent>
                <CardFooter className="justify-center">
                    <p className="text-sm text-muted-foreground">
                        Already have an account?{" "}
                        <Link to="/login" className="underline hover:text-primary">
                            Login
                        </Link>
                    </p>
                </CardFooter>
            </Card>
        </AuthLayout>
    );
}
