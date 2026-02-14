import { sveltekit } from "@sveltejs/kit/vite"
import { defineConfig } from "vite"

export default defineConfig({
    plugins: [sveltekit()],
    build: {
        rollupOptions: {
            output: {
                manualChunks: (id) => (id.includes("data.json") ? "data.json" : null),
            },
        },
    },
})
