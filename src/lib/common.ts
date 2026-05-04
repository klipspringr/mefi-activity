export const SUBSITES = {
    mefi: "MetaFilter",
    askme: "AskMe",
    meta: "MetaTalk",
    music: "Music",
    fanfare: "FanFare",
} as const
export const SITES = { all: "All sites", ...SUBSITES } as const
export const SITES_KEYS = Object.keys(SITES) as (keyof typeof SITES)[]
export const SUBSITES_KEYS = Object.keys(SUBSITES) as (keyof typeof SUBSITES)[]
export type TSite = keyof typeof SITES
export const isSite = (value: string): value is TSite => value in SITES

export const PERIODS = {
    all: "All time",
    since2010: "Since 2010",
    since2020: "Since 2020",
    last10y: "Last 10 years",
    last5y: "Last 5 years",
    last2y: "Last 2 years",
} as const
export type TPeriod = keyof typeof PERIODS
export const isPeriod = (value: string): value is TPeriod => value in PERIODS

// need to keep these consistent with config.py
export const ACTIVITY_LEVELS = [1, 5, 10, 25, 50] as const
export const AGE_LABELS = ["<1 yr", "1-5 yrs", "5-10 yrs", "10-15 yrs", "15-20 yrs", "20+ yrs"] as const
export const TOP_N = [0.01, 0.05, 0.1] as const

export const COLORS = {
    white: "rgb(255, 255, 255)",
    posts: "rgb(153, 102, 255)",
    comments: "rgb(75, 192, 192)",
    deleted: "rgb(255, 99, 132)",
    users_new: "rgb(75, 192, 192)",
    users_registered: "rgb(174, 214, 229)",
    sites: {
        all: "rgb(51, 65, 85)",
        mefi: "rgb(54, 162, 235)",
        askme: "rgb(75, 192, 192)",
        meta: "rgb(255, 159, 64)",
        music: "rgb(255, 99, 132)",
        fanfare: "rgb(153, 102, 255)",
    },
    sequence: [
        "rgb(54, 162, 235)",
        "rgb(255, 205, 86)",
        "rgb(255, 159, 64)",
        "rgb(255, 99, 132)",
        "rgb(153, 102, 255)",
        "rgb(75, 192, 192)",
        "rgb(201, 203, 207)",
    ],
} as const

const largeFormatter = Intl.NumberFormat(undefined, { useGrouping: true })
export const large = (n: number) => largeFormatter.format(n)

const compactFormatter = Intl.NumberFormat(undefined, { notation: "compact", compactDisplay: "short" })
export const compact = (n: number) => compactFormatter.format(n)

const hourFormatter = Intl.DateTimeFormat(undefined, { hour12: true, hour: "numeric", timeZone: "UTC" })
export const hour = (n: Date | number) => hourFormatter.format(n)

const monthYearFormatter = Intl.DateTimeFormat(undefined, { month: "long", year: "numeric" })
export const monthYear = (n: Date | number) => monthYearFormatter.format(n)

export const PERCENT_OPTIONS: Intl.NumberFormatOptions = {
    style: "percent",
    minimumFractionDigits: 0,
    maximumFractionDigits: 1,
}

export const total = (arr: number[]) => arr.reduce((t, c) => t + c, 0)
