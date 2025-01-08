import type { Config } from "tailwindcss"
import * as defaultTheme from "tailwindcss/defaultTheme"

export default {
    content: ["./src/**/*.{html,js,svelte,ts}"],
    theme: {
        extend: {
            colors: {
                "mefi-blue": "rgb(6, 90, 143)",
                "mefi-green": "rgb(156, 199, 84)",
                "mefi-dark": "rgb(3, 67, 109)",
                "mefi-pale": "rgb(136, 194, 216)",
                "mefi-paler": "rgb(174, 214, 229)",
            },
            fontFamily: {
                sans: ["Reddit Sans", ...defaultTheme.fontFamily.sans],
            },
        },
        screens: {
            xs: "390px",
            ...defaultTheme.screens,
        },
    },
    plugins: [],
} satisfies Config
