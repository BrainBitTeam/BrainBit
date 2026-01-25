import { defineConfig, Plugin } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import fs from "fs";
import { componentTagger } from "lovable-tagger";

// ZCU102 board IP address - change this to match your board
const ZCU102_IP = "192.168.1.11";
const ZCU102_PORT = 8080;

// Path to local radio_status.json file in root folder
//path.resolve(__dirname../../home/root/, "radio_status.json");
const RADIO_STATUS_FILE = path.resolve(__dirname, "dist/radio_state.json");

// Plugin to serve radio state from local file
function serveRadioState(): Plugin {
  return {
    name: "serve-radio-state",
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        if (req.url === "/radio-status.json" || req.url?.startsWith("/radio-status.json?")) {
          if (req.method === "GET") {
            try {
              const data = fs.readFileSync(RADIO_STATUS_FILE, "utf-8");
              res.setHeader("Content-Type", "application/json");
              res.setHeader("Cache-Control", "no-cache, no-store, must-revalidate");
              res.end(data);
            } catch (err) {
              res.statusCode = 500;
              res.end(JSON.stringify({ error: "Failed to read radio_status.json" }));
            }
            return;
          }
        }
        next();
      });
    },
  };
}

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
  },
  plugins: [
    react(),
    mode === "development" && componentTagger(),
    serveRadioState(),
  ].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
