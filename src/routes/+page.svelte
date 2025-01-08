<script lang="ts">
    import { browser } from "$app/environment"
    import ChartTitle from "$lib/ChartTitle.svelte"
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
    import { Chart } from "svelte-chartjs"
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
    } as const
    const SITES_KEYS = Object.keys(SITES) as Array<keyof typeof SITES>

    const MONTH_LATEST = json["all"]._start_month - 1 + json["all"].posts.length
    const TIMESERIES_FILTERS = {
        "All time": undefined,
        "Since 2010": new Date(2010, 0, 1).getTime(),
        "Since 2020": new Date(2020, 0, 1).getTime(),
        "Last 10 years": new Date(json["all"]._start_year, MONTH_LATEST - 120, 1).getTime(),
        "Last 5 years": new Date(json["all"]._start_year, MONTH_LATEST - 60, 1).getTime(),
        "Last 2 years": new Date(json["all"]._start_year, MONTH_LATEST - 24, 1).getTime(),
    } as const

    // need to keep these consistent with config.py
    const ACTIVITY_LEVELS = [1, 5, 10, 25, 50]
    const AGE_LABELS = ["<1 year", "1-5 years", "5-10 years", "10-15 years", "15+ years"]
    const TOP_N = [0.01, 0.05, 0.1]

    const COLORS = {
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
            fanfare: "rgb(153, 102, 255)",
            music: "rgb(255, 99, 132)",
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
    }

    const color = (i: number) => COLORS.sequence[i % COLORS.sequence.length]

    const NUMBER_FORMAT = Intl.NumberFormat(undefined, { useGrouping: true })
    const COMPACT_FORMAT = Intl.NumberFormat(undefined, { notation: "compact", compactDisplay: "short" })
    const HOUR_FORMAT = Intl.DateTimeFormat(undefined, { hour12: true, hour: "numeric", timeZone: "UTC" })

    const PERCENT_OPTIONS = {
        style: "percent",
        minimumFractionDigits: 0,
        maximumFractionDigits: 1,
    } as Intl.NumberFormatOptions

    const LINE_CHART_TYPE = "line" as ChartType // stop TypeScript complaining
    const BAR_CHART_TYPE = "bar" as ChartType

    let showJumpMenu = false

    let filterSite: keyof typeof SITES = "all"
    let timeSeriesMin: number | undefined

    ChartJS.defaults.animation = false
    ChartJS.defaults.responsive = true
    ChartJS.defaults.maintainAspectRatio = false

    ChartJS.defaults.parsing = false
    ChartJS.defaults.normalized = true

    ChartJS.defaults.datasets.bar.barPercentage = 1
    ChartJS.defaults.datasets.bar.categoryPercentage = 1
    ChartJS.defaults.datasets.line.pointStyle = false

    ChartJS.defaults.scales.linear.beginAtZero = true
    ChartJS.defaults.scales.linear.grid = { display: true, z: 1 }
    ChartJS.defaults.scales.timeseries.grid = { display: true, z: 1 }
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

    const tickCompact = (v: string | number) => (typeof v === "number" ? COMPACT_FORMAT.format(v) : v)

    const tooltipUsersTotal = (ctx: TooltipItem<"bar">[]) =>
        "Total monthly active: " + NUMBER_FORMAT.format(activeUsers[ctx[0].dataIndex])

    const tooltipPerDay = (ctx: TooltipItem<"bar">[]) =>
        "Per day: " + NUMBER_FORMAT.format(Math.round(ctx[0].parsed.y / (365 / 12)))

    const constructData = (series: number[], mapFn?: (v: number, i: number) => number, categoryLabels = false) =>
        series.map((v, i) => ({
            x: categoryLabels ? i : monthlyLabels[i],
            y: mapFn ? mapFn(v, i) : v,
        }))

    const padSeriesLeft = (site: keyof typeof SITES, series: number[], value: number): number[] =>
        Array(json["all"].posts.length - json[site].posts.length)
            .fill(value)
            .concat(series)

    // calculate total posts excluding AskMe, for denominator on deleted posts percentage chart
    const askMePostsPadded = padSeriesLeft("askme", json["askme"].posts, 0)
    const totalPostsExAskMe = json["all"].posts.map((n, i) => n - askMePostsPadded[i])

    $: monthlyLabels = json[filterSite].posts.map((_, i) =>
        new Date(json[filterSite]._start_year, json[filterSite]._start_month + i - 1, 1).getTime()
    )

    $: activeUsers = json[filterSite].users_monthly[0]
</script>

<svelte:head>
    <title>MetaFilter activity stats</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
    <link href="https://fonts.googleapis.com/css2?family=Reddit+Sans:wght@200..900&display=swap" rel="stylesheet" />
</svelte:head>

<div class="mx-auto max-w-[1280px] xl:border-x xl:border-mefi-paler">
    <header class="sticky top-0 z-20 mb-2 select-none">
        <div class="flex h-10 items-center bg-mefi-blue text-white">
            <h1 class="grow pl-4 text-lg xs:text-2xl">
                <a href="/" class="tracking-wide !no-underline">
                    <span class="font-semibold uppercase text-white">MetaFilter</span>
                    <span class="font-extrabold text-mefi-green">Activity Stats</span>
                </a>
            </h1>
            <button class="h-full pl-2 pr-4 hover:text-mefi-paler" on:click={() => (showJumpMenu = !showJumpMenu)}>
                <svg width="2rem" height="2rem" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M4 6H20M4 12H20M4 18H20" stroke="currentColor" stroke-width="3" />
                </svg>
            </button>
        </div>
        <div class="flex h-12 items-center gap-2 bg-mefi-dark px-4">
            <div class="text-sm font-semibold uppercase tracking-wider text-mefi-paler xs:text-base">Filter</div>
            <select bind:value={filterSite} id="filterSite">
                {#each Object.entries(SITES) as [key, name]}
                    <option value={key}>{name}</option>
                {/each}
            </select>
            <select bind:value={timeSeriesMin} id="timeSeriesMin">
                {#each Object.entries(TIMESERIES_FILTERS) as [label, value]}
                    <option {value}>{label}</option>
                {/each}
            </select>
        </div>
    </header>

    <h2 class="menu-ignore">Notes</h2>
    <ul class="mb-4 ml-4 list-outside list-disc px-2 marker:text-mefi-blue sm:px-4">
        <li>
            Data is from the <a href="https://stuff.metafilter.com/infodump/">MetaFilter Infodump</a> published on
            <strong>{json._published}</strong>. Infodump updates show here within 24 hours.
        </li>
        <li>
            Any problems or comments, <a href="https://www.metafilter.com/user/304523">MeFi Mail me</a>
            or <a href="https://github.com/klipspringr/mefi-activity/issues">open an issue</a>.
            <a href="https://github.com/klipspringr/mefi-activity">Source on GitHub</a>. Not affiliated with MetaFilter
            LLC.
        </li>
        <li>
            <strong>Active users</strong> means users who made <strong>at least one comment or post</strong> on the
            selected site in the given month. For different definitions of activity, see
            <a href="#monthly_users_by_number_of_posts_and_comments">this chart</a>.
        </li>
    </ul>

    <h2>Users</h2>
    <div class="chart">
        <ChartTitle text="Monthly active users" />
        <div class="chartjs">
            <Chart
                type="bar"
                data={{
                    datasets: json[filterSite].users_monthly_by_joined.map((counts, i) => ({
                        label: "Joined " + (json._start_joinyear + i),
                        data: constructData(counts),
                        backgroundColor: color(i),
                    })),
                }}
                options={{
                    scales: {
                        x: { stacked: true, type: "timeseries", min: timeSeriesMin },
                        y: { stacked: true, ticks: { callback: tickCompact } },
                    },
                    plugins: { tooltip: { callbacks: { afterTitle: tooltipUsersTotal } } },
                }} />
        </div>
    </div>
    <div class="chart">
        <ChartTitle text="Monthly active users by year joined" />
        <div class="chartjs">
            <Chart
                type="bar"
                data={{
                    datasets: json[filterSite].users_monthly_by_joined.map((counts, i) => ({
                        label: "Joined " + (json._start_joinyear + i),
                        data: constructData(counts, (v, j) => v / activeUsers[j]),
                        backgroundColor: color(i),
                    })),
                }}
                options={{
                    scales: {
                        x: { stacked: true, type: "timeseries", min: timeSeriesMin },
                        y: { stacked: true, max: 1, ticks: { format: PERCENT_OPTIONS } },
                    },
                    plugins: { tooltip: { callbacks: { afterTitle: tooltipUsersTotal } } },
                }} />
        </div>
    </div>
    <div class="chart">
        <ChartTitle text="Monthly users by number of posts and comments" />
        <div class="chartjs tall">
            <Chart
                type="bar"
                data={{
                    datasets: json[filterSite].users_monthly.map((counts, level) => ({
                        label: `${ACTIVITY_LEVELS[level]}+`,
                        data: constructData(counts),
                        backgroundColor: color(level),
                        order: -level,
                    })),
                }}
                options={{
                    scales: {
                        x: { stacked: true, type: "timeseries", min: timeSeriesMin },
                        y: { stacked: false, ticks: { callback: tickCompact } },
                    },
                    interaction: { mode: "index" },
                    plugins: { legend: { display: true, reverse: true } },
                }} />
        </div>
    </div>
    <div class="chart">
        <ChartTitle text="New and cumulative active users" />
        <div class="chartjs">
            <Chart
                type="bar"
                data={{
                    datasets: [
                        {
                            type: "bar",
                            label: "Users first active (R axis)",
                            data: constructData(json[filterSite].users_new),
                            backgroundColor: COLORS.users_new,
                            yAxisID: "y_new",
                            order: 1,
                        },
                        {
                            type: "line",
                            label: "Users ever active (L axis)",
                            data: constructData(json[filterSite].users_cum),
                            borderColor: COLORS.sites.all,
                            backgroundColor: COLORS.white,
                            yAxisID: "y_cum",
                        },
                    ],
                }}
                options={{
                    scales: {
                        x: { type: "timeseries", min: timeSeriesMin },
                        y_cum: {
                            type: "linear",
                            position: "left",
                            ticks: { callback: tickCompact },
                        },
                        y_new: {
                            type: "linear",
                            position: "right",
                            grid: { drawOnChartArea: false },
                            ticks: { callback: tickCompact },
                        },
                    },
                    interaction: { mode: "index" },
                    plugins: { legend: { display: true } },
                }} />
        </div>
    </div>
    <div class="chart">
        <ChartTitle text="Cumulative registered and active users" />
        <div class="chartjs tall">
            <Chart
                type="line"
                data={{
                    datasets: SITES_KEYS.map((site) => ({
                        type: LINE_CHART_TYPE,
                        label: String(SITES[site]),
                        data: constructData(padSeriesLeft(site, json[site].users_cum, NaN)),
                        borderColor: COLORS.sites[site],
                        backgroundColor: COLORS.white,
                    })).concat({
                        type: BAR_CHART_TYPE,
                        label: "Registered users",
                        data: constructData(json["all"].users_registered),
                        borderColor: COLORS.users_registered,
                        backgroundColor: COLORS.users_registered,
                    }),
                }}
                options={{
                    scales: {
                        x: { type: "timeseries", min: timeSeriesMin },
                        y: { ticks: { callback: tickCompact } },
                    },
                    interaction: { mode: "index" },
                    plugins: { legend: { display: true } },
                }} />
        </div>
        <div class="note">
            Lines show users who made at least one post or comment on a given site. Registered users are higher,
            reflecting users who never post or comment. User ID numbers are higher still, because the site allocates an
            ID before signup is completed.
        </div>
    </div>

    <h2>Activity distribution</h2>
    <div class="chart">
        <ChartTitle text="Posts and comments by user account age" />
        <div class="chartjs tall">
            <Chart
                type="bar"
                data={{
                    datasets: json[filterSite].activity_by_age.map((counts, i) => ({
                        label: AGE_LABELS[i],
                        data: constructData(
                            counts,
                            (c, j) => c / (json[filterSite].posts[j] + json[filterSite].comments[j])
                        ),
                        backgroundColor: color(i),
                    })),
                }}
                options={{
                    scales: {
                        x: { stacked: true, type: "timeseries", min: timeSeriesMin },
                        y: { stacked: true, max: 1, ticks: { format: PERCENT_OPTIONS } },
                    },
                    interaction: { mode: "index" },
                    plugins: { legend: { display: true } },
                }} />
        </div>
        <div class="note">User account age at time of posting or commenting.</div>
    </div>
    <div class="chart">
        <ChartTitle text="Posts by most active posters" />
        <div class="chartjs">
            <Chart
                type="bar"
                data={{
                    datasets: json[filterSite].posts_top_users.map((counts, i) => ({
                        label: `Top ${TOP_N[i] * 100}%`,
                        data: constructData(counts),
                        backgroundColor: color(i),
                    })),
                }}
                options={{
                    scales: {
                        x: { stacked: true, type: "timeseries", min: timeSeriesMin },
                        y: { stacked: false, max: 0.6, ticks: { format: PERCENT_OPTIONS } },
                    },
                    interaction: { mode: "index" },
                    plugins: { legend: { display: true } },
                }} />
        </div>
        <div class="note">Percentage of posts made by the <em>n</em> per cent of users who made the most posts.</div>
    </div>
    <div class="chart">
        <ChartTitle text="Comments by most active commenters" />
        <div class="chartjs">
            <Chart
                type="bar"
                data={{
                    datasets: json[filterSite].comments_top_users.map((counts, i) => ({
                        label: `Top ${TOP_N[i] * 100}%`,
                        data: constructData(counts),
                        backgroundColor: color(i),
                    })),
                }}
                options={{
                    scales: {
                        x: { stacked: true, type: "timeseries", min: timeSeriesMin },
                        y: { stacked: false, max: 0.7, ticks: { format: PERCENT_OPTIONS } },
                    },
                    interaction: { mode: "index" },
                    plugins: { legend: { display: true } },
                }} />
        </div>
        <div class="note">
            Percentage of comments made by the <em>n</em> per cent of users who made the most comments.
        </div>
    </div>

    <h2>Posts and comments</h2>
    <div class="chart">
        <ChartTitle text="Posts" />
        <div class="chartjs">
            <Chart
                type="bar"
                data={{
                    datasets: [
                        {
                            label: "Posts",
                            data: constructData(json[filterSite].posts),
                            backgroundColor: COLORS.posts,
                        },
                    ],
                }}
                options={{
                    scales: {
                        x: { type: "timeseries", min: timeSeriesMin },
                        y: { ticks: { callback: tickCompact } },
                    },
                    plugins: { tooltip: { callbacks: { footer: tooltipPerDay } } },
                }} />
        </div>
    </div>
    <div class="chart">
        <ChartTitle text="Comments" />
        <div class="chartjs">
            <Chart
                type="bar"
                data={{
                    datasets: [
                        {
                            label: "Comments",
                            data: constructData(json[filterSite].comments),
                            backgroundColor: COLORS.comments,
                        },
                    ],
                }}
                options={{
                    scales: {
                        x: { type: "timeseries", min: timeSeriesMin },
                        y: { ticks: { callback: tickCompact } },
                    },
                    plugins: { tooltip: { callbacks: { footer: tooltipPerDay } } },
                }} />
        </div>
    </div>
    <div class="chart">
        <ChartTitle text="Posts per active user" />
        <div class="chartjs">
            <Chart
                type="line"
                data={{
                    datasets: [
                        {
                            label: "Posts per active user",
                            data: constructData(json[filterSite].posts, (v, i) => v / activeUsers[i]),
                            borderColor: COLORS.posts,
                        },
                    ],
                }}
                options={{
                    scales: { x: { type: "timeseries", min: timeSeriesMin ?? new Date(2001, 0, 1).getTime() } },
                }} />
        </div>
        <div class="note">
            1999 and 2000 are excluded so later years are readable. September 1999 saw 20 posts per active user.
        </div>
    </div>
    <div class="chart">
        <ChartTitle text="Comments per active user" />
        <div class="chartjs">
            <Chart
                type="line"
                data={{
                    datasets: [
                        {
                            label: "Comments per active user",
                            data: constructData(json[filterSite].comments, (v, i) => v / activeUsers[i]),
                            borderColor: COLORS.comments,
                        },
                    ],
                }}
                options={{
                    scales: { x: { type: "timeseries", min: timeSeriesMin } },
                }} />
        </div>
    </div>
    <div class="chart">
        <ChartTitle text="Comments per post" />
        <div class="chartjs">
            <Chart
                type="line"
                data={{
                    datasets: [
                        {
                            label: "Comments per post",
                            data: constructData(json[filterSite].comments, (v, i) => v / json[filterSite].posts[i]),
                            borderColor: COLORS.comments,
                        },
                    ],
                }}
                options={{
                    scales: { x: { type: "timeseries", min: timeSeriesMin } },
                }} />
        </div>
    </div>
    <div class="chart">
        <ChartTitle text="Deleted posts" />
        <div class="chartjs">
            <Chart
                type="bar"
                data={{
                    datasets: [
                        {
                            label: "Percentage of posts deleted",
                            data: constructData(
                                json[filterSite].posts_deleted,
                                (v, i) => v / (filterSite === "all" ? totalPostsExAskMe : json[filterSite].posts)[i]
                            ),
                            backgroundColor: COLORS.deleted,
                        },
                    ],
                }}
                options={{
                    scales: {
                        x: { type: "timeseries", min: timeSeriesMin },
                        y: { ticks: { format: PERCENT_OPTIONS } },
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                afterTitle: ([{ dataIndex }]) => [
                                    "Deleted: " + NUMBER_FORMAT.format(json[filterSite].posts_deleted[dataIndex]),
                                    filterSite === "all"
                                        ? "Total (ex AskMe): " + NUMBER_FORMAT.format(totalPostsExAskMe[dataIndex])
                                        : "Total: " + NUMBER_FORMAT.format(json[filterSite].posts[dataIndex]),
                                ],
                            },
                        },
                    },
                }} />
        </div>
        <div class="note">Infodump excludes deleted Ask MetaFilter questions.</div>
    </div>

    <h2>Activity by time period</h2>
    <div class="chart">
        <ChartTitle text="Posts and comments by day of week" />
        <div class="chartjs">
            <Chart
                type="bar"
                data={{
                    labels: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                    datasets: [
                        {
                            label: "Posts",
                            data: constructData(json[filterSite].posts_weekdays_percent, undefined, true),
                            backgroundColor: COLORS.posts,
                        },
                        {
                            label: "Comments",
                            data: constructData(json[filterSite].comments_weekdays_percent, undefined, true),
                            backgroundColor: COLORS.comments,
                        },
                    ],
                }}
                options={{
                    datasets: { bar: { categoryPercentage: 0.9, barPercentage: 1 } },
                    scales: { y: { max: 0.2, ticks: { format: PERCENT_OPTIONS } } },
                    interaction: { mode: "index" },
                    plugins: { legend: { display: true } },
                }} />
        </div>
    </div>
    <div class="chart">
        <ChartTitle text="Posts and comments by hour" />
        <div class="chartjs">
            <Chart
                type="bar"
                data={{
                    labels: Array.from({ length: 24 }, (_, i) => HOUR_FORMAT.format(i * 60 * 60 * 1000)),
                    datasets: [
                        {
                            label: "Posts",
                            data: constructData(json[filterSite].posts_hours_percent, undefined, true),
                            backgroundColor: COLORS.posts,
                        },
                        {
                            label: "Comments",
                            data: constructData(json[filterSite].comments_hours_percent, undefined, true),
                            backgroundColor: COLORS.comments,
                        },
                    ],
                }}
                options={{
                    datasets: { bar: { categoryPercentage: 0.9, barPercentage: 1 } },
                    scales: { y: { max: 0.07, ticks: { format: PERCENT_OPTIONS } } },
                    interaction: { mode: "index" },
                    plugins: { legend: { display: true } },
                }} />
        </div>
        <div class="note">
            Post and comment timestamps are Pacific Time. Day of week and hour charts can be filtered by site but not by
            time period.
        </div>
    </div>
</div>

<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
<!-- svelte-ignore a11y-click-events-have-key-events -->
<menu
    class="fixed right-0 top-0 z-50 h-screen max-w-[85vw] overflow-y-auto border-mefi-blue bg-white p-4 text-lg transition-transform duration-300 ease-in-out"
    class:translate-x-0={showJumpMenu}
    class:translate-x-full={!showJumpMenu}
    class:border-l-4={showJumpMenu}>
    <ul class="space-y-1">
        <li><a href="#top" on:click={() => (showJumpMenu = false)}>Top</a></li>
        {#if browser}
            {#each document.querySelectorAll("h2:not(.menu-ignore), h3") as h}
                {#if h.tagName === "H2"}
                    <li class="pt-4 text-base font-black uppercase tracking-[0.15em] text-mefi-pale">
                        {h.textContent}
                    </li>
                {:else}
                    <li>
                        <a href="#{h.id}" on:click={() => (showJumpMenu = false)}>{h.childNodes[0].textContent}</a>
                    </li>
                {/if}
            {/each}
        {/if}
    </ul>
</menu>

{#if showJumpMenu}
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <div class="fixed left-0 top-0 z-40 h-screen w-screen bg-mefi-blue/90" on:click={() => (showJumpMenu = false)}>
    </div>
{/if}

<style lang="postcss">
    :global(h1, h2, h3) {
        @apply select-none font-black;
    }

    h2 {
        @apply mb-2 bg-mefi-paler px-2 py-1 text-base uppercase tracking-[0.15em] text-mefi-blue sm:px-4;
    }

    a {
        @apply font-semibold text-mefi-blue underline decoration-mefi-pale decoration-2 underline-offset-2 hover:decoration-mefi-blue;
    }

    div.chart {
        @apply mb-8 px-2 sm:px-4;
    }

    div.chartjs {
        @apply relative h-[60vw] sm:h-[50vw] sm:max-h-[640px];
    }

    div.chartjs.tall {
        @apply h-[70vw] sm:h-[50vw];
    }

    div.note {
        @apply mt-2 text-sm before:mr-1 before:text-xs before:font-black before:uppercase before:text-mefi-blue before:content-["Note"] sm:text-base;
    }

    header select,
    header select > option {
        @apply rounded-full bg-mefi-blue py-1 pl-2 pr-4 text-sm font-semibold text-white xs:text-base;
    }

    header select:has(option:not(:first-child):checked) {
        @apply bg-mefi-paler text-mefi-dark ring-4 ring-white;
    }

    :global(::selection) {
        @apply bg-mefi-blue text-white;
    }
</style>
