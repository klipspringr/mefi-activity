<script lang="ts">
    import ChartTitle from "$lib/ChartTitle.svelte"
    import { toAnchor } from "$lib/util"
    import {
        BarController,
        BarElement,
        CategoryScale,
        Chart as ChartJS,
        Colors,
        Legend,
        LineController,
        LineElement,
        LinearScale,
        PointElement,
        TimeSeriesScale,
        Tooltip,
        type ActiveElement,
        type ChartType,
        type Point,
        type TooltipItem,
    } from "chart.js"
    import "chartjs-adapter-date-fns"
    import { Bar, Chart, Line } from "svelte-chartjs"
    import "../app.css"
    import * as json from "../data/data.json"

    ChartJS.register(
        BarController,
        BarElement,
        CategoryScale,
        Colors,
        Legend,
        LinearScale,
        LineController,
        LineElement,
        PointElement,
        TimeSeriesScale,
        Tooltip
    )

    const SITES = {
        all: "All sites",
        mefi: "MetaFilter",
        askme: "Ask MetaFilter",
        meta: "MetaTalk",
        fanfare: "FanFare",
        music: "Music",
    }
    const SITES_KEYS = Object.keys(SITES) as Array<keyof typeof SITES>
    const TIMESERIES_FILTERS = ["All time", "Since 2010", "Last 10 years", "Last 2 years"]
    const AGE_LABELS = ["<1 year", "1-5 years", "5-10 years", "10-15 years", "15+ years"]

    const COLORS = {
        posts: "rgb(6, 90, 143)",
        comments: "rgb(136, 194, 216)",
        posts_deleted: "rgb(3, 67, 109)",
        users_new: "rgb(136, 194, 216)",
        users_cum: "rgb(6, 90, 143)",
        users_registered: "rgb(226, 232, 240)",
        site_all: "rgb(51, 65, 85)",
        site_mefi: "rgb(54, 162, 235)",
        site_askme: "rgb(75, 192, 192)",
        site_meta: "rgb(255, 159, 64)",
        site_fanfare: "rgb(153, 102, 255)",
        site_music: "rgb(255, 99, 132)",
    }

    const NUM_FORMAT = Intl.NumberFormat()

    const LINE_CHART_TYPE = "line" as ChartType // stop TypeScript complaining
    const BAR_CHART_TYPE = "bar" as ChartType

    let chartsSectionElement: HTMLElement
    let showJumpMenu = false

    let filterSite: keyof typeof SITES = "all"
    let filterTimeSeries: string
    let timeSeriesMin: number | undefined

    ChartJS.defaults.animation = false
    ChartJS.defaults.responsive = true
    ChartJS.defaults.maintainAspectRatio = false

    ChartJS.defaults.normalized = true

    ChartJS.defaults.datasets.bar.barPercentage = 1
    ChartJS.defaults.datasets.bar.categoryPercentage = 1
    ChartJS.defaults.datasets.line.pointStyle = false

    ChartJS.defaults.scales.linear.beginAtZero = true
    ChartJS.defaults.scales.timeseries.grid = { display: true }
    ChartJS.defaults.scales.timeseries.time.tooltipFormat = "MMMM yyyy"
    ChartJS.defaults.scales.timeseries.ticks.callback = (v) => {
        const d = new Date(v)
        return d.getMonth() == 6 ? d.getFullYear() : undefined
    }

    ChartJS.defaults.plugins.legend.display = false
    ChartJS.defaults.plugins.legend.position = "bottom"
    ChartJS.defaults.plugins.legend.onClick = () => {}

    Tooltip.positioners.cursor = (_: ActiveElement[], eventPos: Point) => eventPos
    ChartJS.defaults.plugins.tooltip.position = "cursor"

    const timeSeriesLabels = Object.fromEntries(
        SITES_KEYS.map((site) => [
            site,
            Array.from({ length: json[site].users_monthly.length }, (_, i) =>
                new Date(json[site]._start_year, json[site]._start_month + i - 1, 1).getTime()
            ),
        ])
    )

    const tickThousands = (v: string | number) => (typeof v === "number" && v >= 1000 ? v / 1000 + "K" : v)

    const tooltipUsersTotal = (ctx: TooltipItem<"bar">[]) =>
        "Total monthly active: " + NUM_FORMAT.format(json[filterSite].users_monthly[ctx[0].dataIndex])

    const tooltipPerDay = (ctx: TooltipItem<"bar">[]) =>
        "Per day: " + NUM_FORMAT.format(Math.round(ctx[0].parsed.y / (365 / 12)))

    const padSeriesLeft = (site: keyof typeof SITES, series: number[]) =>
        Array(timeSeriesLabels["all"].length - timeSeriesLabels[site].length)
            .fill(0)
            .concat(series)

    // calculate total posts excluding AskMe, for denominator on deleted posts percentage chart
    const askMePostsPadded = padSeriesLeft("askme", json["askme"].posts)
    const totalPostsExAskMe = json["all"].posts.map((n, i) => n - askMePostsPadded[i])

    $: {
        switch (filterTimeSeries) {
            case "Since 2010":
                timeSeriesMin = new Date(2010, 0, 1).getTime()
                break
            case "Last 10 years":
                timeSeriesMin = timeSeriesLabels[filterSite].at(-120)
                break
            case "Last 2 years":
                timeSeriesMin = timeSeriesLabels[filterSite].at(-24)
                break
            default:
                timeSeriesMin = undefined
        }
    }
</script>

<svelte:head>
    <title>MetaFilter activity stats</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
    <link href="https://fonts.googleapis.com/css2?family=Reddit+Sans:wght@200..900&display=swap" rel="stylesheet" />
</svelte:head>

<div class="mx-auto max-w-[1280px] xl:border-x xl:border-mefi-paler">
    <header class="sticky top-0 z-20 select-none">
        <div class="flex h-10 items-center bg-mefi-blue text-white">
            <h1 class="grow pl-4 text-lg xs:text-2xl">
                <a href="/">
                    <span class="font-semibold uppercase">MetaFilter</span>
                    <span class="font-black tracking-wider text-mefi-green">Activity Stats</span>
                </a>
            </h1>
            <button class="h-full pl-2 pr-4 hover:text-mefi-paler" on:click={() => (showJumpMenu = !showJumpMenu)}>
                <svg width="2rem" height="2rem" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M4 6H20M4 12H20M4 18H20" stroke="currentColor" stroke-width="3" />
                </svg>
            </button>
        </div>
        <div class="flex h-12 items-center gap-2 bg-mefi-dark px-4">
            <div class="hidden font-semibold uppercase tracking-wider text-mefi-paler xs:block">Filter</div>
            <select bind:value={filterSite} id="filterSite">
                {#each Object.entries(SITES) as [key, name]}
                    <option value={key}>{name}</option>
                {/each}
            </select>
            <select bind:value={filterTimeSeries} id="filterTimeSeries">
                {#each TIMESERIES_FILTERS as key}
                    <option value={key}>{key}</option>
                {/each}
            </select>
        </div>
    </header>

    <section>
        <h2 class="!mb-2 !mt-2">Notes</h2>
        <ul class="ml-6 list-outside list-disc marker:text-mefi-blue">
            <li>
                <a href="https://stuff.metafilter.com/infodump/">Infodump</a> data from
                <strong>{json._published}</strong>. Infodump updates show here within 24 hours.
            </li>
            <li>
                <b>Active users</b> made at least <b>one post or comment</b> on the selected site in the month.
                <b>Registered users</b> completed the sign-up process.
            </li>
            <li>
                Any problems or comments, <a href="https://www.metafilter.com/user/304523">MeFi Mail me</a> or
                <a href="https://github.com/klipspringr/mefi-activity/issues">open an issue</a> on
                <a href="https://github.com/klipspringr/mefi-activity">GitHub</a>.
                <b>Not affiliated with MetaFilter LLC.</b>
            </li>
        </ul>
    </section>

    <section bind:this={chartsSectionElement}>
        <h2 class="!mt-4">Users</h2>

        <ChartTitle text="Monthly active users" />
        <div class="chart-container">
            <Bar
                data={{
                    labels: timeSeriesLabels[filterSite],
                    datasets: Object.entries(json[filterSite].users_monthly_by_joined).map(([year, counts]) => ({
                        label: "Joined " + year,
                        data: counts,
                    })),
                }}
                options={{
                    scales: {
                        y: {
                            stacked: true,
                            ticks: {
                                callback: tickThousands,
                            },
                        },
                        x: {
                            stacked: true,
                            type: "timeseries",
                            min: timeSeriesMin,
                        },
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                afterTitle: tooltipUsersTotal,
                            },
                        },
                    },
                }} />
        </div>

        <ChartTitle text="Monthly active users by year joined" />
        <div class="chart-container">
            <Bar
                data={{
                    labels: timeSeriesLabels[filterSite],
                    datasets: Object.entries(json[filterSite].users_monthly_by_joined).map(([year, counts]) => ({
                        label: "Joined " + year,
                        data: counts.map((v, i) => v / json[filterSite].users_monthly[i]),
                    })),
                }}
                options={{
                    scales: {
                        y: {
                            stacked: true,
                            max: 1,
                            ticks: {
                                format: {
                                    style: "percent",
                                    minimumFractionDigits: 0,
                                    maximumFractionDigits: 1,
                                },
                            },
                        },
                        x: {
                            stacked: true,
                            type: "timeseries",
                            min: timeSeriesMin,
                        },
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                afterTitle: tooltipUsersTotal,
                            },
                        },
                    },
                }} />
        </div>

        <ChartTitle text="New and cumulative active users" />
        <div class="chart-container">
            <Chart
                type="bar"
                data={{
                    labels: timeSeriesLabels[filterSite],
                    datasets: [
                        {
                            type: "bar",
                            label: "Users first active (R axis)",
                            data: json[filterSite].users_new,
                            backgroundColor: COLORS.users_new,
                            yAxisID: "y_new",
                            order: 1,
                        },
                        {
                            type: "line",
                            label: "Users ever active (L axis)",
                            data: json[filterSite].users_cum,
                            borderColor: COLORS.users_cum,
                            yAxisID: "y_cum",
                        },
                    ],
                }}
                options={{
                    scales: {
                        y_cum: {
                            type: "linear",
                            position: "left",
                            ticks: {
                                callback: tickThousands,
                            },
                        },
                        y_new: {
                            type: "linear",
                            position: "right",
                            grid: {
                                drawOnChartArea: false,
                            },
                            ticks: {
                                callback: tickThousands,
                            },
                        },
                        x: {
                            type: "timeseries",
                            min: timeSeriesMin,
                        },
                    },
                    interaction: {
                        mode: "index",
                    },
                    plugins: {
                        legend: {
                            display: true,
                        },
                    },
                }} />
        </div>

        <ChartTitle text="Cumulative registered and active users" />
        <div class="chart-container-tall">
            <Chart
                type="line"
                data={{
                    labels: timeSeriesLabels["all"],
                    datasets: [
                        {
                            type: BAR_CHART_TYPE,
                            label: "Registered users",
                            data: json["all"].users_registered_cum,
                            backgroundColor: COLORS.users_registered,
                            order: 10,
                        },
                        {
                            type: LINE_CHART_TYPE,
                            label: `Active on any site`,
                            data: json["all"].users_cum,
                            borderColor: COLORS.site_all,
                            backgroundColor: COLORS.site_all,
                        },
                        {
                            type: LINE_CHART_TYPE,
                            label: `Active on MeFi`,
                            data: padSeriesLeft("mefi", json["mefi"].users_cum),
                            borderColor: COLORS.site_mefi,
                            backgroundColor: COLORS.site_mefi,
                        },
                        {
                            type: LINE_CHART_TYPE,
                            label: `Active on AskMe`,
                            data: padSeriesLeft("askme", json["askme"].users_cum),
                            borderColor: COLORS.site_askme,
                            backgroundColor: COLORS.site_askme,
                        },
                        {
                            type: LINE_CHART_TYPE,
                            label: `Active on MeTa`,
                            data: padSeriesLeft("meta", json["meta"].users_cum),
                            borderColor: COLORS.site_meta,
                            backgroundColor: COLORS.site_meta,
                        },
                        {
                            type: LINE_CHART_TYPE,
                            label: `Active on Fanfare`,
                            data: padSeriesLeft("fanfare", json["fanfare"].users_cum),
                            borderColor: COLORS.site_fanfare,
                            backgroundColor: COLORS.site_fanfare,
                        },
                        {
                            type: LINE_CHART_TYPE,
                            label: `Active on Music`,
                            data: padSeriesLeft("music", json["music"].users_cum),
                            borderColor: COLORS.site_music,
                            backgroundColor: COLORS.site_music,
                        },
                    ],
                }}
                options={{
                    scales: {
                        x: {
                            type: "timeseries",
                            min: timeSeriesMin,
                        },
                        y: {
                            ticks: {
                                callback: tickThousands,
                            },
                        },
                    },
                    interaction: {
                        mode: "index",
                    },
                    plugins: {
                        legend: {
                            display: true,
                        },
                    },
                }} />
        </div>

        <h2>Posts and comments</h2>

        <ChartTitle text="Posts" />
        <div class="chart-container">
            <Bar
                data={{
                    labels: timeSeriesLabels[filterSite],
                    datasets: [
                        {
                            data: json[filterSite].posts,
                            backgroundColor: COLORS.posts,
                        },
                    ],
                }}
                options={{
                    scales: {
                        x: { type: "timeseries", min: timeSeriesMin },
                        y: {
                            ticks: {
                                callback: tickThousands,
                            },
                        },
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                footer: tooltipPerDay,
                            },
                        },
                    },
                }} />
        </div>
        <ChartTitle text="Comments" />
        <div class="chart-container">
            <Bar
                data={{
                    labels: timeSeriesLabels[filterSite],
                    datasets: [{ data: json[filterSite].comments, backgroundColor: COLORS.comments }],
                }}
                options={{
                    scales: {
                        x: { type: "timeseries", min: timeSeriesMin },
                        y: {
                            ticks: {
                                callback: tickThousands,
                            },
                        },
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                footer: tooltipPerDay,
                            },
                        },
                    },
                }} />
        </div>
        <ChartTitle text="Posts and comments by user account age" />
        <div class="chart-container-tall">
            <Bar
                data={{
                    labels: timeSeriesLabels[filterSite],
                    datasets: json[filterSite].activity_by_age.map((counts, i) => ({
                        label: AGE_LABELS[i],
                        data: counts.map((c, j) => c / (json[filterSite].posts[j] + json[filterSite].comments[j])),
                    })),
                }}
                options={{
                    scales: {
                        y: {
                            stacked: true,
                            max: 1,
                            ticks: {
                                format: {
                                    style: "percent",
                                    minimumFractionDigits: 0,
                                    maximumFractionDigits: 1,
                                },
                            },
                        },
                        x: {
                            stacked: true,
                            type: "timeseries",
                            min: timeSeriesMin,
                        },
                    },
                    interaction: {
                        mode: "index",
                    },
                    plugins: {
                        legend: {
                            display: true,
                        },
                    },
                }} />
        </div>
        <p class="note">User account age at time of posting or commenting.</p>

        <ChartTitle text="Posts per active user" />
        <div class="chart-container">
            <Line
                data={{
                    labels: timeSeriesLabels[filterSite],
                    datasets: [
                        {
                            data: json[filterSite].posts.map((v, i) => v / json[filterSite].users_monthly[i]),
                            borderColor: COLORS.posts,
                        },
                    ],
                }}
                options={{
                    scales: {
                        x: {
                            type: "timeseries",
                            min: timeSeriesMin,
                        },
                        y: {
                            max: filterSite == "all" || filterSite == "mefi" ? 2 : undefined,
                        },
                    },
                }} />
        </div>

        <ChartTitle text="Comments per active user" />
        <div class="chart-container">
            <Line
                data={{
                    labels: timeSeriesLabels[filterSite],
                    datasets: [
                        {
                            data: json[filterSite].comments.map((v, i) => v / json[filterSite].users_monthly[i]),
                            borderColor: COLORS.comments,
                        },
                    ],
                }}
                options={{
                    scales: {
                        x: {
                            type: "timeseries",
                            min: timeSeriesMin,
                        },
                    },
                }} />
        </div>

        <ChartTitle text="Comments per post" />
        <div class="chart-container">
            <Line
                data={{
                    labels: timeSeriesLabels[filterSite],
                    datasets: [
                        {
                            data: json[filterSite].comments.map((v, i) => v / json[filterSite].posts[i]),
                            borderColor: COLORS.comments,
                        },
                    ],
                }}
                options={{
                    scales: {
                        x: {
                            type: "timeseries",
                            min: timeSeriesMin,
                        },
                    },
                }} />
        </div>

        <ChartTitle text="Deleted posts" />
        <div class="chart-container">
            <Bar
                data={{
                    labels: timeSeriesLabels[filterSite],
                    datasets: [
                        {
                            label: "Percentage of posts deleted",
                            data: json[filterSite].posts_deleted.map(
                                (v, i) => v / (filterSite === "all" ? totalPostsExAskMe : json[filterSite].posts)[i]
                            ),
                            backgroundColor: COLORS.posts_deleted,
                        },
                    ],
                }}
                options={{
                    scales: {
                        x: { type: "timeseries", min: timeSeriesMin },
                        y: {
                            ticks: {
                                format: {
                                    style: "percent",
                                    minimumFractionDigits: 0,
                                    maximumFractionDigits: 1,
                                },
                            },
                        },
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                afterTitle: (ctx) => [
                                    "Deleted: " + NUM_FORMAT.format(json[filterSite].posts_deleted[ctx[0].dataIndex]),
                                    "Total: " +
                                        NUM_FORMAT.format(
                                            (filterSite === "all" ? totalPostsExAskMe : json[filterSite].posts)[
                                                ctx[0].dataIndex
                                            ]
                                        ),
                                ],
                            },
                        },
                    },
                }} />
        </div>
        <p class="note">Excludes Ask MetaFilter, as the Infodump does not contain deleted questions.</p>

        <h2>Activity by time period</h2>

        <ChartTitle text="Posts and comments by day of week" />
        <div class="chart-container">
            <Bar
                data={{
                    labels: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                    datasets: [
                        {
                            label: "Posts",
                            data: json[filterSite].posts_weekdays_percent,
                            backgroundColor: COLORS.posts,
                        },
                        {
                            label: "Comments",
                            data: json[filterSite].comments_weekdays_percent,
                            backgroundColor: COLORS.comments,
                        },
                    ],
                }}
                options={{
                    datasets: {
                        bar: {
                            categoryPercentage: 0.9,
                            barPercentage: 1,
                        },
                    },
                    scales: {
                        y: {
                            max: 0.2,
                            ticks: {
                                format: {
                                    style: "percent",
                                    minimumFractionDigits: 0,
                                    maximumFractionDigits: 1,
                                },
                            },
                        },
                    },
                    interaction: {
                        mode: "index",
                    },
                    plugins: {
                        legend: {
                            display: true,
                        },
                    },
                }} />
        </div>

        <ChartTitle text="Posts and comments by hour" />
        <div class="chart-container">
            <Bar
                data={{
                    labels: [...Array(24).keys()],
                    datasets: [
                        {
                            label: "Posts",
                            data: json[filterSite].posts_hours_percent,
                            backgroundColor: COLORS.posts,
                        },
                        {
                            label: "Comments",
                            data: json[filterSite].comments_hours_percent,
                            backgroundColor: COLORS.comments,
                        },
                    ],
                }}
                options={{
                    datasets: {
                        bar: {
                            categoryPercentage: 0.9,
                            barPercentage: 1,
                        },
                    },
                    scales: {
                        y: {
                            max: 0.07,
                            ticks: {
                                format: {
                                    style: "percent",
                                    minimumFractionDigits: 0,
                                    maximumFractionDigits: 1,
                                },
                            },
                        },
                    },
                    interaction: {
                        mode: "index",
                    },
                    plugins: {
                        legend: {
                            display: true,
                        },
                    },
                }} />
        </div>
        <p class="note">Timestamps are recorded on the MetaFilter server in Pacific Time.</p>
    </section>
</div>

<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
<!-- svelte-ignore a11y-click-events-have-key-events -->
<menu
    class="fixed right-0 top-0 z-50 h-screen max-w-[85vw] overflow-y-auto border-mefi-blue bg-white p-4 text-lg transition-transform duration-300 ease-in-out"
    class:translate-x-0={showJumpMenu}
    class:translate-x-full={!showJumpMenu}
    class:border-l-4={showJumpMenu}>
    <ul class="space-y-1">
        <li><h2 class="!mt-0 !text-mefi-blue">Jump to chart</h2></li>
        <li><a href="#top" class="block" on:click={() => (showJumpMenu = false)}>Top</a></li>
        {#each chartsSectionElement?.querySelectorAll("h2, h3") || [] as h}
            <li>
                {#if h.tagName === "H2"}
                    <h2>{h.childNodes[0].textContent}</h2>
                {:else if h.tagName === "H3"}
                    <a
                        href="#{toAnchor(h.childNodes[0].textContent)}"
                        class="block"
                        on:click={() => (showJumpMenu = false)}>{h.childNodes[0].textContent}</a>
                {/if}
            </li>
        {/each}
    </ul>
</menu>

{#if showJumpMenu}
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="fixed left-0 top-0 z-40 h-screen w-screen bg-mefi-blue/90" on:click={() => (showJumpMenu = false)}>
    </div>
{/if}

<style lang="postcss">
    :global(body) {
        @apply pb-4;
    }

    :global(h1, h2, h3) {
        @apply select-none font-black;
    }

    section {
        @apply px-2 sm:px-4;
    }

    section h2 {
        @apply -mx-2 -mb-6 mt-8 bg-mefi-paler px-2 py-1 text-base uppercase tracking-[0.15em] text-mefi-blue sm:-mx-4 sm:px-4;
    }

    div.chart-container {
        @apply relative h-[60vw] sm:h-[50vw] sm:max-h-[640px];
    }

    div.chart-container-tall {
        @apply relative h-[80vw] sm:h-[50vw] sm:max-h-[640px];
    }

    p.note {
        @apply mx-2 before:mr-2 before:text-xs before:font-black before:uppercase before:text-mefi-blue before:content-["Note:"];
    }

    menu h2 {
        @apply mt-4 text-base uppercase tracking-[0.15em] text-mefi-pale;
    }

    section a,
    menu a {
        @apply font-semibold text-mefi-blue underline decoration-mefi-pale decoration-2 underline-offset-2 hover:decoration-mefi-blue;
    }

    header select,
    header option {
        @apply rounded-full bg-mefi-paler py-1 pl-2 pr-4 text-sm font-semibold text-mefi-blue xs:text-base;
    }

    :global(::selection) {
        @apply bg-mefi-blue text-white;
    }
</style>
