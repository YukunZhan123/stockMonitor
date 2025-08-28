import { useState } from "react";
import { useAuth } from "../context/AuthContext";

export default function RegisterForm({ onSuccess, onSwitchToLogin }) {
  const { register } = useAuth();
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors((prev) => ({
        ...prev,
        [name]: "",
      }));
    }
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.username.trim()) {
      newErrors.username = "Username is required";
    } else if (formData.username.trim().length < 3) {
      newErrors.username = "Username must be at least 3 characters";
    }

    if (!formData.email.trim()) {
      newErrors.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = "Please enter a valid email address";
    }

    if (!formData.password) {
      newErrors.password = "Password is required";
    } else if (formData.password.length < 6) {
      newErrors.password = "Password must be at least 6 characters";
    }

    if (!formData.confirmPassword) {
      newErrors.confirmPassword = "Please confirm your password";
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = "Passwords do not match";
    }

    return newErrors;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const newErrors = validateForm();
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setLoading(true);
    setErrors({});

    const result = await register({
      username: formData.username,
      email: formData.email,
      password: formData.password,
      password_confirm: formData.confirmPassword
    });
    
    if (result.success) {
      onSuccess(result.user);
    } else if (result.fieldErrors) {
      // Handle field-specific validation errors from backend
      const backendErrors = {};
      
      // Map backend field names to frontend field names
      Object.keys(result.fieldErrors).forEach(field => {
        const errorMessages = result.fieldErrors[field];
        const errorMessage = Array.isArray(errorMessages) ? errorMessages[0] : errorMessages;
        
        if (field === 'non_field_errors') {
          backendErrors.general = errorMessage;
        } else if (field === 'password_confirm') {
          backendErrors.confirmPassword = errorMessage;
        } else {
          backendErrors[field] = errorMessage;
        }
      });
      
      setErrors(backendErrors);
    } else {
      setErrors({ general: result.error });
    }
    
    setLoading(false);
  };

  return (
    <div className="flex min-h-full flex-col justify-center px-6 py-12 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-sm">
        <img 
          src="https://tailwindcss.com/plus-assets/img/logos/mark.svg?color=indigo&shade=500" 
          alt="Your Company" 
          className="mx-auto h-10 w-auto" 
        />
        <h2 className="mt-10 text-center text-2xl/9 font-bold tracking-tight text-white">
          Create your account
        </h2>
      </div>

      <div className="mt-10 sm:mx-auto sm:w-full sm:max-w-sm">
        {errors.general && (
          <div className="mb-4 rounded-md bg-red-500/10 border border-red-500/20 px-4 py-3">
            <p className="text-sm text-red-300">{errors.general}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="username" className="block text-sm/6 font-medium text-gray-100">
              Username
            </label>
            <div className="mt-2">
              <input 
                id="username" 
                type="text" 
                name="username" 
                value={formData.username}
                onChange={handleChange}
                required 
                autoComplete="username"
                disabled={loading}
                className={`block w-full rounded-md bg-white/5 px-3 py-1.5 text-base text-white outline-1 -outline-offset-1 placeholder:text-gray-500 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-500 sm:text-sm/6 ${
                  errors.username 
                    ? "outline-red-500/50 focus:outline-red-500" 
                    : "outline-white/10"
                }`}
                placeholder="Choose a username"
              />
              {errors.username && (
                <p className="mt-1 text-sm text-red-300">{errors.username}</p>
              )}
            </div>
          </div>

          <div>
            <label htmlFor="email" className="block text-sm/6 font-medium text-gray-100">
              Email address
            </label>
            <div className="mt-2">
              <input 
                id="email" 
                type="email" 
                name="email" 
                value={formData.email}
                onChange={handleChange}
                required 
                autoComplete="email"
                disabled={loading}
                className={`block w-full rounded-md bg-white/5 px-3 py-1.5 text-base text-white outline-1 -outline-offset-1 placeholder:text-gray-500 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-500 sm:text-sm/6 ${
                  errors.email 
                    ? "outline-red-500/50 focus:outline-red-500" 
                    : "outline-white/10"
                }`}
                placeholder="Enter your email"
              />
              {errors.email && (
                <p className="mt-1 text-sm text-red-300">{errors.email}</p>
              )}
            </div>
          </div>

          <div>
            <label htmlFor="password" className="block text-sm/6 font-medium text-gray-100">
              Password
            </label>
            <div className="mt-2">
              <input 
                id="password" 
                type="password" 
                name="password" 
                value={formData.password}
                onChange={handleChange}
                required 
                autoComplete="new-password"
                disabled={loading}
                className={`block w-full rounded-md bg-white/5 px-3 py-1.5 text-base text-white outline-1 -outline-offset-1 placeholder:text-gray-500 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-500 sm:text-sm/6 ${
                  errors.password 
                    ? "outline-red-500/50 focus:outline-red-500" 
                    : "outline-white/10"
                }`}
                placeholder="Create a password"
              />
              {errors.password && (
                <p className="mt-1 text-sm text-red-300">{errors.password}</p>
              )}
            </div>
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm/6 font-medium text-gray-100">
              Confirm password
            </label>
            <div className="mt-2">
              <input 
                id="confirmPassword" 
                type="password" 
                name="confirmPassword" 
                value={formData.confirmPassword}
                onChange={handleChange}
                required 
                autoComplete="new-password"
                disabled={loading}
                className={`block w-full rounded-md bg-white/5 px-3 py-1.5 text-base text-white outline-1 -outline-offset-1 placeholder:text-gray-500 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-500 sm:text-sm/6 ${
                  errors.confirmPassword 
                    ? "outline-red-500/50 focus:outline-red-500" 
                    : "outline-white/10"
                }`}
                placeholder="Confirm your password"
              />
              {errors.confirmPassword && (
                <p className="mt-1 text-sm text-red-300">{errors.confirmPassword}</p>
              )}
            </div>
          </div>

          <div>
            <button 
              type="submit" 
              disabled={loading}
              className="flex w-full justify-center rounded-md bg-indigo-500 px-3 py-1.5 text-sm/6 font-semibold text-white hover:bg-indigo-400 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <div className="flex items-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Creating account...
                </div>
              ) : (
                "Create account"
              )}
            </button>
          </div>
        </form>

        <p className="mt-10 text-center text-sm/6 text-gray-400">
          Already a member?{" "}
          <button
            type="button"
            onClick={onSwitchToLogin}
            className="font-semibold text-indigo-400 hover:text-indigo-300"
          >
            Sign in to your account
          </button>
        </p>
      </div>
    </div>
  );
}