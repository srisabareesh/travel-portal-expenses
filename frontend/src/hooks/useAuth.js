import { useContext } from "react";

import { AuthContext } from "../context/auth-context.js";

export function useAuth() {
  return useContext(AuthContext);
}

export default useAuth;
