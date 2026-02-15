<script lang="ts">
    import { browser } from "$app/environment"
    import { goto } from "$app/navigation"
    import ChartComponent from "$lib/ChartComponent.svelte"
    import {
        ACTIVITY_LEVELS,
        AGE_LABELS,
        COLORS,
        compact,
        hour,
        large,
        monthYear,
        PERCENT_OPTIONS,
        PERIODS,
        SITES,
        SITES_KEYS,
        TOP_N,
        type TPeriod,
        type TSite,
    } from "$lib/common"
    import type { ChartDataset, ChartTypeRegistry, TooltipItem } from "chart.js"
    import {
        BarController,
        BarElement,
        CategoryScale,
        Chart,
        Colors,
        Legend,
        LinearScale,
        LineController,
        LineElement,
        PointElement,
        TimeSeriesScale,
        Tooltip,
        type ActiveElement,
        type Point,
    } from "chart.js"
    import { fade } from "svelte/transition"
    import "../app.css"
    import * as json from "../data/data.json"
    import type { PageProps } from "./$types"

    let { data }: PageProps = $props()

    const updateURL = (key: string, value: string) => {
        const url = new URL(window.location.href)
        url.searchParams.set(key, value)
        goto(url, { replaceState: true, noScroll: true })
    }

    const hideJumpMenu = () => (showJumpMenu = false)

    const tickCompact = (v: string | number) => (typeof v === "number" ? compact(v) : v)

    const daysInMonth = (timestamp: number) => {
        const d = new Date(timestamp)
        return new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate() // zeroth day of next month = last day of this month
    }

    const tooltipUsersTotal = (ctx: TooltipItem<keyof ChartTypeRegistry>[]) =>
        "Total users: " + large(usersSite[ctx[0].dataIndex])

    const tooltipPerDay = (ctx: TooltipItem<keyof ChartTypeRegistry>[]) =>
        "Per day: " + large(Math.round((ctx[0].parsed.y ?? 0) / daysInMonth(ctx[0].parsed.x ?? 0)))

    const padSeriesLeft = (site: TSite, series: number[], value: number): number[] =>
        Array(json["all"].posts.length - json[site].posts.length)
            .fill(value)
            .concat(series)

    const color = (i: number) => COLORS.sequence[i % COLORS.sequence.length]

    /* Chart.js configuration */
    Chart.register(
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

    Chart.defaults.animation = false
    Chart.defaults.responsive = true
    Chart.defaults.maintainAspectRatio = false

    Chart.defaults.datasets.bar.barPercentage = 1
    Chart.defaults.datasets.bar.categoryPercentage = 1
    Chart.defaults.datasets.line.pointStyle = false

    Chart.defaults.scales.linear.beginAtZero = true
    Chart.defaults.scales.timeseries.time.tooltipFormat = "MMMM yyyy"

    // this is hacky, but the alternatives all have weird side effects
    Chart.defaults.scales.timeseries.ticks.callback = (v) => {
        const d = new Date(v)
        return d.getMonth() === 6 ? d.getFullYear() : undefined
    }

    Chart.defaults.plugins.legend.display = false
    Chart.defaults.plugins.legend.position = "bottom"
    Chart.defaults.plugins.legend.onClick = () => {}

    Tooltip.positioners.cursor = (_: ActiveElement[], eventPos: Point) => eventPos
    Chart.defaults.plugins.tooltip.position = "cursor"

    /* Parsing and derived data */
    const firstMonth = new Date(json["all"]._start_year, json["all"]._start_month - 1, 1)
    const latestMonthIndex = json["all"]._start_month - 1 + json["all"].posts.length - 1
    const latestCompletedMonth = new Date(json["all"]._start_year, latestMonthIndex, 1)

    const timeSeriesMinimums: Record<TPeriod, number> = {
        all: 0,
        since2010: new Date(2010, 0, 1).getTime(),
        since2020: new Date(2020, 0, 1).getTime(),
        last10y: new Date(json["all"]._start_year, latestMonthIndex - 10 * 12 + 1, 1).getTime(),
        last5y: new Date(json["all"]._start_year, latestMonthIndex - 5 * 12 + 1, 1).getTime(),
        last2y: new Date(json["all"]._start_year, latestMonthIndex - 2 * 12 + 1, 1).getTime(),
    }

    const monthLabelsAll = Array.from({ length: json["all"].posts.length }, (_, i) =>
        new Date(json["all"]._start_year, json["all"]._start_month + i - 1, 1).getTime()
    )

    // total posts excluding AskMe, for denominator on deleted posts percentage chart
    const postsAsk = padSeriesLeft("askme", json["askme"].posts, 0)
    const postsExcludingAsk = json["all"].posts.map((n, i) => n - postsAsk[i])

    const totalPosts = json["all"].posts.reduce((t, c) => t + c, 0)
    const totalComments = json["all"].comments.reduce((t, c) => t + c, 0)
    const totalUsers = json["all"].users_registered[json["all"].users_registered.length - 1]

    /* UI and stores */
    let showJumpMenu = $state(false)

    let timeSeriesMin = $derived(timeSeriesMinimums[data.period])

    let monthLabelsSite = $derived(monthLabelsAll.slice(json["all"].posts.length - json[data.site].posts.length))

    let usersSite = $derived(json[data.site].users_monthly[0])
</script>

<svelte:head>
    <title>MetaFilter activity stats</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
    <link href="https://fonts.googleapis.com/css2?family=Reddit+Sans:wght@200..900&display=swap" rel="stylesheet" />
    <link rel="canonical" href="https://mefist.at/" />
</svelte:head>

<div class="mx-auto max-w-screen-xl pb-4 xl:border-x xl:border-mefi-paler">
    <header class="sticky top-0 z-20 mb-2 select-none">
        <div class="flex h-10 items-center gap-x-2 bg-mefi-blue text-white sm:gap-x-4">
            <h1 class="pl-4 text-lg xs:text-2xl">
                <a href="/" class="uppercase tracking-wide !no-underline">
                    <span class="font-extrabold text-white">MeFi</span><span class="font-semibold text-mefi-green"
                        >St.at</span>
                </a>
            </h1>
            <div class="grow translate-y-px text-sm/none font-medium tracking-wide text-mefi-paler sm:text-base/none">
                MetaFilter activity stats
            </div>
            <button
                class="h-full pl-2 pr-4 hover:text-mefi-paler"
                onclick={() => (showJumpMenu = !showJumpMenu)}
                aria-label="Toggle menu">
                <svg width="2rem" height="2rem" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M4 6H20M4 12H20M4 18H20" stroke="currentColor" stroke-width="3" />
                </svg>
            </button>
        </div>
        <div class="flex h-12 items-center gap-2 bg-mefi-dark px-4">
            <div class="text-sm font-semibold uppercase tracking-wider text-mefi-paler xs:text-base">Filter</div>
            <select id="filterSite" onchange={(e) => updateURL("site", e.currentTarget.value)}>
                {#each Object.entries(SITES) as [value, label]}
                    <option {value} selected={value === data.site ? true : null}>{label}</option>
                {/each}
            </select>
            <select id="timeSeriesMin" onchange={(e) => updateURL("time", e.currentTarget.value)}>
                {#each Object.entries(PERIODS) as [value, label]}
                    <option {value} selected={value === data.period ? true : null}>{label}</option>
                {/each}
            </select>
        </div>
    </header>

    <h2 data-menu-ignore>Notes</h2>
    <ul class="mb-4 ml-4 list-outside list-disc px-4 marker:text-mefi-blue">
        <li>
            Data from the <a href="https://stuff.metafilter.com/infodump/">MetaFilter Infodump</a> published
            <strong>{json._published}</strong>. Infodump updates appear here within 24 hours.
        </li>
        <li>
            Data runs from <strong>{monthYear(firstMonth)}</strong> to
            <strong>{monthYear(latestCompletedMonth)}</strong> (the most recent full month in the Infodump).
        </li>
        <li>
            <strong>{large(totalUsers)}</strong> registered users,
            <strong>{large(totalPosts)}</strong> posts,
            <strong>{large(totalComments)}</strong> comments.
        </li>
        <li>
            Questions or comments? <a href="https://www.metafilter.com/user/304523">MeFi Mail Klipspringer</a>
            or <a href="https://github.com/klipspringr/mefi-activity/issues">open an issue</a>.
            <a href="https://github.com/klipspringr/mefi-activity">Source on GitHub</a>. Not an official MetaFilter
            product.
        </li>
    </ul>

    <!-- <div class="bg-rose-100 px-4 py-2 text-sm font-bold text-rose-600 sm:text-base">
        <strong>[DATESTAMP]</strong> [NOTICE]
    </div> -->

    <h2>Users</h2>
    <ChartComponent
        title="Users who posted or commented"
        titleForAnchor="Monthly active users"
        type="bar"
        data={{
            labels: monthLabelsSite,
            datasets: json[data.site].users_monthly_by_joined.map((counts, i) => ({
                label: "Joined in " + (json._start_joinyear + i),
                data: counts,
                backgroundColor: color(i),
            })),
        }}
        options={{
            scales: {
                x: { stacked: true, type: "timeseries", min: timeSeriesMin, grid: { z: 1 } },
                y: { stacked: true, ticks: { callback: tickCompact }, grid: { z: 1 } },
            },
            plugins: { tooltip: { callbacks: { afterTitle: tooltipUsersTotal } } },
        }} />
    <ChartComponent
        title="Users who posted or commented, by year joined"
        titleForAnchor="Monthly active users by year joined"
        type="bar"
        data={{
            labels: monthLabelsSite,
            datasets: json[data.site].users_monthly_by_joined.map((counts, i) => ({
                label: "Joined in " + (json._start_joinyear + i),
                data: counts.map((v, j) => v / usersSite[j]),
                backgroundColor: color(i),
            })),
        }}
        options={{
            scales: {
                x: { stacked: true, type: "timeseries", min: timeSeriesMin, grid: { z: 1 } },
                y: { stacked: true, max: 1, ticks: { format: PERCENT_OPTIONS }, grid: { z: 1 } },
            },
            plugins: { tooltip: { callbacks: { afterTitle: tooltipUsersTotal } } },
        }} />
    <ChartComponent
        title="Users by number of posts and comments"
        titleForAnchor="Monthly users by number of posts and comments"
        type="bar"
        data={{
            labels: monthLabelsSite,
            datasets: json[data.site].users_monthly.map((counts, level) => ({
                label: `${ACTIVITY_LEVELS[level]}+`,
                data: counts,
                backgroundColor: color(level),
                order: -level,
            })),
        }}
        options={{
            scales: {
                x: { stacked: true, type: "timeseries", min: timeSeriesMin, grid: { z: 1 } },
                y: { stacked: false, ticks: { callback: tickCompact }, grid: { z: 1 } },
            },
            interaction: { mode: "index" },
            plugins: { legend: { display: true, reverse: true } },
        }}
        tall />
    <ChartComponent
        title="Users first and last active"
        type="bar"
        data={{
            labels: monthLabelsSite,
            datasets: [
                {
                    type: "line",
                    label: "Net",
                    data: json[data.site].users_first.map((v, i) => v - json[data.site].users_last[i]),
                    backgroundColor: COLORS.sites.all,
                    borderColor: COLORS.sites.all,
                },
                {
                    type: "bar",
                    label: "Users first active",
                    data: json[data.site].users_first,
                    backgroundColor: COLORS.users_new,
                },
                {
                    type: "bar",
                    label: "Users last active",
                    data: json[data.site].users_last.map((v) => -v),
                    backgroundColor: COLORS.deleted,
                },
            ],
        }}
        options={{
            scales: {
                x: { type: "timeseries", stacked: true, min: timeSeriesMin, grid: { z: 1 } },
                y: {
                    type: "linear",
                    ticks: { callback: tickCompact },
                    grid: { z: 1 },
                    afterDataLimits: function (scale) {
                        const max = Math.min(1000, Math.max(Math.abs(scale.min), Math.abs(scale.max)))
                        scale.min = -max
                        scale.max = max
                    },
                },
            },
            interaction: { mode: "index" },
            plugins: { legend: { display: true } },
        }}>
        Number of users who made their first (or last) post or comment on the site in the given month.
        <strong>Take care interpreting this chart:</strong> recent months will naturally show large numbers of users last
        active. This doesn't imply they permanently left the site.
    </ChartComponent>
    <ChartComponent
        title="Cumulative number of users"
        titleForAnchor="Cumulative registered and active users"
        type="line"
        data={{
            labels: monthLabelsAll,
            datasets: [
                ...SITES_KEYS.map(
                    (site): ChartDataset => ({
                        type: "line",
                        label: String(SITES[site]),
                        data: padSeriesLeft(site, json[site].users_cum, NaN),
                        borderColor: COLORS.sites[site],
                        backgroundColor: COLORS.sites[site],
                    })
                ),
                {
                    type: "bar",
                    label: "Registered users",
                    data: json["all"].users_registered,
                    borderColor: COLORS.users_registered,
                    backgroundColor: COLORS.users_registered,
                },
            ],
        }}
        options={{
            scales: {
                x: { type: "timeseries", min: timeSeriesMin, grid: { z: 1 } },
                y: { ticks: { callback: tickCompact }, grid: { z: 1 } },
            },
            interaction: { mode: "index" },
            plugins: { legend: { display: true } },
        }}
        tall>
        <strong>Registered users (shaded area)</strong> completed the signup process.
        <strong>Users (lines)</strong> made at least one post or comment on the given site.
        <strong>User ID numbers</strong> (not shown) are much higher, because the site allocates an ID number for incomplete
        signups.
    </ChartComponent>

    <h2>Activity distribution</h2>
    <ChartComponent
        title="Posts and comments by user account age"
        type="bar"
        data={{
            labels: monthLabelsSite,
            datasets: json[data.site].activity_by_age.map((counts, i) => ({
                label: AGE_LABELS[i],
                data: counts.map((c, j) => c / (json[data.site].posts[j] + json[data.site].comments[j])),
                backgroundColor: color(i),
            })),
        }}
        options={{
            scales: {
                x: { stacked: true, type: "timeseries", min: timeSeriesMin, grid: { z: 1 } },
                y: { stacked: true, max: 1, ticks: { format: PERCENT_OPTIONS }, grid: { z: 1 } },
            },
            interaction: { mode: "index" },
            plugins: { legend: { display: true } },
        }}
        tall>
        Age in years of user account at time of posting or commenting.
    </ChartComponent>
    <ChartComponent
        title="Posts by most active posters"
        type="bar"
        data={{
            labels: monthLabelsSite,
            datasets: json[data.site].posts_top_users.map((counts, i) => ({
                label: `Top ${TOP_N[i] * 100}%`,
                data: counts,
                backgroundColor: color(i),
            })),
        }}
        options={{
            scales: {
                x: { stacked: true, type: "timeseries", min: timeSeriesMin, grid: { z: 1 } },
                y: { stacked: false, max: 0.6, ticks: { format: PERCENT_OPTIONS }, grid: { z: 1 } },
            },
            interaction: { mode: "index" },
            plugins: { legend: { display: true } },
        }}>
        Percentage of posts made by the <em>n</em> per cent of users who made the most posts.
    </ChartComponent>
    <ChartComponent
        title="Comments by most active commenters"
        type="bar"
        data={{
            labels: monthLabelsSite,
            datasets: json[data.site].comments_top_users.map((counts, i) => ({
                label: `Top ${TOP_N[i] * 100}%`,
                data: counts,
                backgroundColor: color(i),
            })),
        }}
        options={{
            scales: {
                x: { stacked: true, type: "timeseries", min: timeSeriesMin, grid: { z: 1 } },
                y: { stacked: false, max: 0.7, ticks: { format: PERCENT_OPTIONS }, grid: { z: 1 } },
            },
            interaction: { mode: "index" },
            plugins: { legend: { display: true } },
        }}>
        Percentage of comments made by the <em>n</em> per cent of users who made the most comments.
    </ChartComponent>

    <h2>Posts and comments</h2>
    <ChartComponent
        title="Posts"
        type="bar"
        data={{
            labels: monthLabelsSite,
            datasets: [
                {
                    label: "Posts",
                    data: json[data.site].posts,
                    backgroundColor: COLORS.posts,
                },
            ],
        }}
        options={{
            scales: {
                x: { type: "timeseries", min: timeSeriesMin, grid: { z: 1 } },
                y: { ticks: { callback: tickCompact }, grid: { z: 1 } },
            },
            plugins: { tooltip: { callbacks: { footer: tooltipPerDay } } },
        }} />
    <ChartComponent
        title="Comments"
        type="bar"
        data={{
            labels: monthLabelsSite,
            datasets: [
                {
                    label: "Comments",
                    data: json[data.site].comments,
                    backgroundColor: COLORS.comments,
                },
            ],
        }}
        options={{
            scales: {
                x: { type: "timeseries", min: timeSeriesMin, grid: { z: 1 } },
                y: { ticks: { callback: tickCompact }, grid: { z: 1 } },
            },
            plugins: { tooltip: { callbacks: { footer: tooltipPerDay } } },
        }} />
    <ChartComponent
        title="Posts per user"
        titleForAnchor="Posts per active user"
        type="line"
        data={{
            labels: monthLabelsSite,
            datasets: [
                {
                    label: "Posts per user",
                    data: json[data.site].posts.map((v, i) => v / usersSite[i]),
                    borderColor: COLORS.posts,
                },
            ],
        }}
        options={{
            scales: { x: { type: "timeseries", min: Math.max(timeSeriesMin, new Date(2001, 0, 1).getTime()) } },
        }}>
        Number of posts divided by number of users who posted or commented at least once in the month. 1999 and 2000 are
        excluded so later years are readable. September 1999 saw 20 posts per user.
    </ChartComponent>
    <ChartComponent
        title="Comments per user"
        titleForAnchor="Comments per active user"
        type="line"
        data={{
            labels: monthLabelsSite,
            datasets: [
                {
                    label: "Comments per user",
                    data: json[data.site].comments.map((v, i) => v / usersSite[i]),
                    borderColor: COLORS.comments,
                },
            ],
        }}
        options={{
            scales: { x: { type: "timeseries", min: timeSeriesMin } },
        }}>
        Number of comments divided by number of users who posted or commented at least once in the month.
    </ChartComponent>
    <ChartComponent
        title="Comments per post"
        type="line"
        data={{
            labels: monthLabelsSite,
            datasets: [
                {
                    label: "Comments per post",
                    data: json[data.site].comments.map((v, i) => v / json[data.site].posts[i]),
                    borderColor: COLORS.comments,
                },
            ],
        }}
        options={{
            scales: { x: { type: "timeseries", min: timeSeriesMin } },
        }} />
    <ChartComponent
        title="Deleted posts"
        type="bar"
        data={{
            labels: monthLabelsSite,
            datasets: [
                {
                    label: "Percentage of posts deleted",
                    data: json[data.site].posts_deleted.map(
                        (v, i) => v / (data.site === "all" ? postsExcludingAsk : json[data.site].posts)[i]
                    ),
                    backgroundColor: COLORS.deleted,
                },
            ],
        }}
        options={{
            scales: {
                x: { type: "timeseries", min: timeSeriesMin, grid: { z: 1 } },
                y: { ticks: { format: PERCENT_OPTIONS }, grid: { z: 1 } },
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        afterTitle: ([{ dataIndex }]) => [
                            "Deleted: " + large(json[data.site].posts_deleted[dataIndex]),
                            data.site === "all"
                                ? "Total (ex AskMe): " + large(postsExcludingAsk[dataIndex])
                                : "Total: " + large(json[data.site].posts[dataIndex]),
                        ],
                    },
                },
            },
        }}>
        Infodump excludes deleted Ask MetaFilter questions.
    </ChartComponent>

    <h2>Activity by time period</h2>
    <ChartComponent
        title="Posts and comments by day of week"
        type="bar"
        data={{
            labels: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            datasets: [
                {
                    label: "Posts",
                    data: json[data.site].posts_weekdays_percent.map((y, x) => ({ x, y })),
                    backgroundColor: COLORS.posts,
                },
                {
                    label: "Comments",
                    data: json[data.site].comments_weekdays_percent.map((y, x) => ({ x, y })),
                    backgroundColor: COLORS.comments,
                },
            ],
        }}
        options={{
            datasets: { bar: { categoryPercentage: 0.9, barPercentage: 1 } },
            scales: { y: { max: 0.2, ticks: { format: PERCENT_OPTIONS }, grid: { z: 1 } } },
            interaction: { mode: "index" },
            plugins: { legend: { display: true } },
        }}>
        Timestamps are recorded on the MetaFilter server in Pacific Time. This chart can't be filtered by time period.
    </ChartComponent>
    <ChartComponent
        title="Posts and comments by hour"
        type="bar"
        data={{
            labels: Array.from({ length: 24 }, (_, i) => hour(i * 60 * 60 * 1000)),
            datasets: [
                {
                    label: "Posts",
                    data: json[data.site].posts_hours_percent,
                    backgroundColor: COLORS.posts,
                },
                {
                    label: "Comments",
                    data: json[data.site].comments_hours_percent,
                    backgroundColor: COLORS.comments,
                },
            ],
        }}
        options={{
            datasets: { bar: { categoryPercentage: 0.9, barPercentage: 1 } },
            scales: { y: { max: 0.07, ticks: { format: PERCENT_OPTIONS }, grid: { z: 1 } } },
            interaction: { mode: "index" },
            plugins: { legend: { display: true } },
        }}>
        Timestamps are recorded on the MetaFilter server in Pacific Time. This chart can't be filtered by time period.
    </ChartComponent>
</div>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<menu
    class="fixed right-0 top-0 z-50 h-screen max-w-[90vw] select-none overflow-y-auto border-mefi-blue bg-white p-4 text-lg transition-transform duration-300 ease-in-out"
    class:translate-x-0={showJumpMenu}
    class:translate-x-full={!showJumpMenu}
    class:border-l-4={showJumpMenu}>
    <ul class="space-y-1">
        <li class="flex items-center justify-between">
            <a href="#top" onclick={hideJumpMenu}>Top</a>
            <button
                class="bg-mefi-paler px-3 py-1 text-3xl/none font-bold text-mefi-blue no-underline hover:text-mefi-dark"
                onclick={hideJumpMenu}>&times;</button>
        </li>
        {#if browser}
            {#each document.querySelectorAll("h2:not([data-menu-ignore]), h3") as h}
                {#if h.tagName === "H2"}
                    <li class="pt-4 text-base font-black uppercase tracking-[0.15em] text-mefi-pale">
                        {h.textContent}
                    </li>
                {:else}
                    <li>
                        <a href="#{h.id}" onclick={hideJumpMenu}>{h.childNodes[0].textContent}</a>
                    </li>
                {/if}
            {/each}
        {/if}
    </ul>
</menu>

{#if showJumpMenu}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div
        class="fixed left-0 top-0 z-40 h-screen w-screen bg-mefi-blue/90"
        transition:fade={{ duration: 200 }}
        onclick={hideJumpMenu}>
    </div>
{/if}

<style lang="postcss">
    :global(h1, h2, h3) {
        @apply font-black;
    }

    h2 {
        @apply mb-2 select-none bg-mefi-paler px-2 py-1 text-base uppercase tracking-[0.15em] text-mefi-blue sm:px-4;
    }

    a {
        @apply font-semibold text-mefi-blue underline decoration-mefi-pale decoration-2 underline-offset-2 hover:decoration-mefi-blue;
    }

    header select,
    header select > option {
        @apply rounded-full bg-mefi-blue py-1 pl-2 pr-4 text-sm font-semibold text-white focus:outline-none xs:text-base;
    }

    header select:has(:global(option:not(:first-child):checked)) {
        @apply bg-mefi-paler text-mefi-dark ring-4 ring-white;
    }

    ::selection {
        @apply bg-mefi-blue text-white;
    }
</style>
