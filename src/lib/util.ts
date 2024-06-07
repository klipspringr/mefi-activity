export const toAnchor = (text: string | null) => (text ? text.trim().toLowerCase().replace(/\W/g, "_") : "")
