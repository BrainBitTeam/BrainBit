import { defineConfig, Plugin } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import fs from "fs";
import { componentTagger } from "lovable-tagger";

// Plugin to serve and update local radio_state.json file
function serveRadioState(): Plugin {
  const jsonPath = "C:/Users/user/Desktop/brainbit/whisper_guard_pc/radio_state.json";

  return {
    name: "serve-radio-state",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        // Strip query params for URL matching (cache-busting params like ?t=...)
        const urlPath = req.url?.split('?')[0];
        if (urlPath === "/api/radio-status.json") {
          // Handle GET - read the file
          if (req.method === "GET") {
            try {
              const data = fs.readFileSync(jsonPath, "utf-8");
              res.setHeader("Content-Type", "application/json");
              res.setHeader("Cache-Control", "no-cache, no-store, must-revalidate");
              res.end(data);
            } catch (err) {
              res.statusCode = 500;
              res.end(JSON.stringify({ error: "Failed to read radio_state.json" }));
            }
            return;
          }

          // Handle POST - update the file
          if (req.method === "POST") {
            let body = "";
            req.on("data", (chunk) => {
              body += chunk.toString();
            });
            req.on("end", () => {
              try {
                const newData = JSON.parse(body);
                // Read existing data and merge
                const existingData = JSON.parse(fs.readFileSync(jsonPath, "utf-8"));
                const mergedData = { ...existingData, ...newData };
                fs.writeFileSync(jsonPath, JSON.stringify(mergedData, null, 2));
                res.setHeader("Content-Type", "application/json");
                res.end(JSON.stringify({ success: true }));
              } catch (err) {
                res.statusCode = 500;
                res.end(JSON.stringify({ error: "Failed to update radio_state.json" }));
              }
            });
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
