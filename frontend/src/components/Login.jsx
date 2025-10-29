import { useState } from "react";
import axios from "axios";
import { API } from "../App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { FileText, Shield, CheckCircle } from "lucide-react";

const Login = ({ onLogin }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    full_name: "",
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const endpoint = isLogin ? "/auth/login" : "/auth/register";
      const payload = isLogin
        ? { email: formData.email, password: formData.password }
        : formData;

      const response = await axios.post(`${API}${endpoint}`, payload);
      onLogin(response.data.access_token, response.data.user);
      toast.success(isLogin ? "Welcome back!" : "Account created successfully!");
    } catch (error) {
      toast.error(
        error.response?.data?.detail || "Authentication failed. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: 'linear-gradient(135deg, #e0f2fe 0%, #dbeafe 100%)' }}>
      <div className="w-full max-w-6xl grid lg:grid-cols-2 gap-8 items-center">
        {/* Left side - Branding */}
        <div className="hidden lg:block space-y-8">
          <div>
            <h1 className="text-5xl font-bold mb-4" style={{ color: '#0369a1' }}>
              ClaimGuard AI
            </h1>
            <p className="text-xl text-gray-700 mb-8">
              Intelligent insurance claim verification powered by advanced AI technology
            </p>
          </div>
          
          <div className="space-y-6">
            <div className="flex items-start gap-4">
              <div className="p-3 rounded-xl" style={{ backgroundColor: '#bae6fd' }}>
                <FileText className="w-6 h-6" style={{ color: '#0369a1' }} />
              </div>
              <div>
                <h3 className="font-semibold text-lg mb-1" style={{ color: '#0c4a6e' }}>Document Analysis</h3>
                <p className="text-gray-600">Upload policy, claims, bills, and medical notes for comprehensive review</p>
              </div>
            </div>
            
            <div className="flex items-start gap-4">
              <div className="p-3 rounded-xl" style={{ backgroundColor: '#bae6fd' }}>
                <Shield className="w-6 h-6" style={{ color: '#0369a1' }} />
              </div>
              <div>
                <h3 className="font-semibold text-lg mb-1" style={{ color: '#0c4a6e' }}>AI-Powered Verification</h3>
                <p className="text-gray-600">Advanced algorithms cross-verify claims against policy rules</p>
              </div>
            </div>
            
            <div className="flex items-start gap-4">
              <div className="p-3 rounded-xl" style={{ backgroundColor: '#bae6fd' }}>
                <CheckCircle className="w-6 h-6" style={{ color: '#0369a1' }} />
              </div>
              <div>
                <h3 className="font-semibold text-lg mb-1" style={{ color: '#0c4a6e' }}>Instant Decisions</h3>
                <p className="text-gray-600">Get pass/fail decisions with detailed reasoning in seconds</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right side - Login form */}
        <Card className="w-full shadow-2xl border-0">
          <CardHeader className="space-y-1">
            <CardTitle className="text-3xl font-bold" style={{ color: '#0369a1' }}>
              {isLogin ? "Welcome Back" : "Create Account"}
            </CardTitle>
            <CardDescription className="text-base">
              {isLogin
                ? "Sign in to analyze your insurance claims"
                : "Start verifying claims with AI"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {!isLogin && (
                <div className="space-y-2">
                  <Label htmlFor="full_name" className="text-sm font-medium">Full Name</Label>
                  <Input
                    id="full_name"
                    data-testid="register-fullname-input"
                    type="text"
                    placeholder="John Doe"
                    value={formData.full_name}
                    onChange={(e) =>
                      setFormData({ ...formData, full_name: e.target.value })
                    }
                    required={!isLogin}
                    className="h-11"
                  />
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="email" className="text-sm font-medium">Email</Label>
                <Input
                  id="email"
                  data-testid="login-email-input"
                  type="email"
                  placeholder="you@example.com"
                  value={formData.email}
                  onChange={(e) =>
                    setFormData({ ...formData, email: e.target.value })
                  }
                  required
                  className="h-11"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password" className="text-sm font-medium">Password</Label>
                <Input
                  id="password"
                  data-testid="login-password-input"
                  type="password"
                  placeholder="••••••••"
                  value={formData.password}
                  onChange={(e) =>
                    setFormData({ ...formData, password: e.target.value })
                  }
                  required
                  className="h-11"
                />
              </div>
              <Button
                data-testid="login-submit-button"
                type="submit"
                className="w-full h-11 text-base font-medium"
                disabled={loading}
                style={{ backgroundColor: '#0369a1', color: 'white' }}
              >
                {loading ? "Processing..." : isLogin ? "Sign In" : "Create Account"}
              </Button>
            </form>
            <div className="mt-6 text-center">
              <button
                data-testid="toggle-auth-mode-button"
                type="button"
                onClick={() => setIsLogin(!isLogin)}
                className="text-sm font-medium hover:underline"
                style={{ color: '#0369a1' }}
              >
                {isLogin
                  ? "Don't have an account? Sign up"
                  : "Already have an account? Sign in"}
              </button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Login;