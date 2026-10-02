// Shim tương thích: re-export từ các module theo domain.
// Code mới nên import trực tiếp, vd: import { getExpiry } from "@/lib/api/alerts";
export * from "./api/client";
export * from "./api/auth";
export * from "./api/templates";
export * from "./api/fleet";
export * from "./api/alerts";
export * from "./api/ops";
export * from "./api/coop";
export * from "./api/system";
