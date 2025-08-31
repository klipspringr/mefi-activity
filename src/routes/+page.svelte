<script lang="ts">
    import { browser } from "$app/environment"
    import { goto } from "$app/navigation"
    import ChartComponent from "$lib/ChartComponent.svelte"
    import {
        ACTIVITY_LEVELS,
        AGE_LABELS,
        COLORS,
        COMPACT_FORMAT,
        HOUR_FORMAT,
        MONTH_FORMAT,
        NUMBER_FORMAT,
        PERCENT_OPTIONS,
        PERIODS,
        SITES,
        SITES_KEYS,
        TOP_N,
        type TPeriod,
        type TSite,
    } from "$lib/common"
    import type { ChartDataset, TooltipItem } from "chart.js"
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

    const tickCompact = (v: string | number) => (typeof v === "number" ? COMPACT_FORMAT.format(v) : v)

    const tooltipUsersTotal = (ctx: TooltipItem<"bar">[]) =>
        "Total monthly active: " + NUMBER_FORMAT.format(activeUsers[ctx[0].dataIndex])

    const daysInMonth = (timestamp: number) => {
        const d = new Date(timestamp)
        return new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate() // zeroth day of next month = last day of this month
    }

    const tooltipPerDay = (ctx: TooltipItem<"bar">[]) =>
        "Per day: " + NUMBER_FORMAT.format(Math.round(ctx[0].parsed.y / daysInMonth(ctx[0].parsed.x)))

    const padSeriesLeft = (site: TSite, series: number[], value: number): number[] =>
        Array(json["all"].posts.length - json[site].posts.length)
            .fill(value)
            .concat(series)

    const color = (i: number) => COLORS.sequence[i % COLORS.sequence.length]

    let showJumpMenu = $state(false)

    const START_YEAR = json["all"]._start_year
    const LATEST_MONTH_INDEX = json["all"]._start_month - 1 + json["all"].posts.length - 1

    const TIMESERIES_MIN: Record<TPeriod, number> = {
        all: 0,
        since2010: new Date(2010, 0, 1).getTime(),
        since2020: new Date(2020, 0, 1).getTime(),
        last10y: new Date(START_YEAR, LATEST_MONTH_INDEX - 10 * 12 + 1, 1).getTime(),
        last5y: new Date(START_YEAR, LATEST_MONTH_INDEX - 5 * 12 + 1, 1).getTime(),
        last2y: new Date(START_YEAR, LATEST_MONTH_INDEX - 2 * 12 + 1, 1).getTime(),
    }

    let timeSeriesMin = $derived(TIMESERIES_MIN[data.period])

    let activeUsers = $derived(json[data.site].users_monthly[0])

    const MONTH_LABELS_ALL = Array.from({ length: json["all"].posts.length }, (_, i) =>
        new Date(json["all"]._start_year, json["all"]._start_month + i - 1, 1).getTime()
    )

    let monthLabelsSite = $derived(MONTH_LABELS_ALL.slice(json["all"].posts.length - json[data.site].posts.length))

    // calculate total posts excluding AskMe, for denominator on deleted posts percentage chart
    const POSTS_ASK = padSeriesLeft("askme", json["askme"].posts, 0)
    const POSTS_EXCLUDING_ASK = json["all"].posts.map((n, i) => n - POSTS_ASK[i])
</script>

<svelte:head>
    <title>MetaFilter activity stats</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
    <link href="https://fonts.googleapis.com/css2?family=Reddit+Sans:wght@200..900&display=swap" rel="stylesheet" />
    <link rel="canonical" href="https://mefist.at/" />
</svelte:head>

<div class="mx-auto max-w-[1280px] pb-4 xl:border-x xl:border-mefi-paler">
    <header class="sticky top-0 z-20 mb-2 select-none">
        <div class="flex h-10 items-center bg-mefi-blue text-white">
            <h1 class="grow pl-4 text-lg xs:text-2xl">
                <a href="/" class="tracking-wide !no-underline">
                    <span class="font-semibold uppercase text-white">MetaFilter</span>
                    <span class="font-extrabold text-mefi-green">Activity Stats</span>
                </a>
            </h1>
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

    <h2 class="menu-ignore">Notes</h2>
    <ul class="mb-4 ml-4 list-outside list-disc px-2 marker:text-mefi-blue sm:px-4">
        <li>
            Data is from the <a href="https://stuff.metafilter.com/infodump/">MetaFilter Infodump</a> published on
            <strong>{json._published}</strong>. Infodump updates show here within 24 hours.
        </li>
        <li>
            Charts run to <strong>{MONTH_FORMAT.format(new Date(START_YEAR, LATEST_MONTH_INDEX, 1))}</strong>, which is
            the last completed month in the Infodump.
        </li>
        <li>
            <strong>Active users</strong> means users who made <strong>at least one comment or post</strong> on the
            selected site in the given month. For a breakdown of users by level of activity, see
            <a href="#monthly_users_by_number_of_posts_and_comments">this chart</a>.
        </li>
        <li>
            Any problems or comments, <a href="https://www.metafilter.com/user/304523">MeFi Mail Klipspringer</a>
            or <a href="https://github.com/klipspringr/mefi-activity/issues">open an issue</a>.
            <a href="https://github.com/klipspringr/mefi-activity">Source on GitHub</a>. Not an official MetaFilter
            product.
        </li>
    </ul>
    <div class="bg-rose-100 px-2 py-2 font-bold text-rose-600 sm:px-4">
        <strong>August 2025 notice:</strong> the Infodump has had some problems recently. Our charts run to the last month
        we have complete data for.
    </div>
    <h2>Users</h2>
    <ChartComponent
        title="Monthly active users"
        type="bar"
        data={{
            labels: monthLabelsSite,
            datasets: json[data.site].users_monthly_by_joined.map((counts, i) => ({
                label: "Joined " + (json._start_joinyear + i),
                data: counts,
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
    <ChartComponent
        title="Monthly active users by year joined"
        type="bar"
        data={{
            labels: monthLabelsSite,
            datasets: json[data.site].users_monthly_by_joined.map((counts, i) => ({
                label: "Joined " + (json._start_joinyear + i),
                data: counts.map((v, j) => v / activeUsers[j]),
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
    <ChartComponent
        title="Monthly users by number of posts and comments"
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
                x: { stacked: true, type: "timeseries", min: timeSeriesMin },
                y: { stacked: false, ticks: { callback: tickCompact } },
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
                x: { type: "timeseries", stacked: true, min: timeSeriesMin },
                y: {
                    type: "linear",
                    ticks: { callback: tickCompact },
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
        Number of users who made their first (or last) post or comment on the site in the given month. Take care
        interpreting this chart: recent months will naturally show large numbers of users last active. This doesn't
        imply they permanently left the site.
    </ChartComponent>
    <ChartComponent
        title="Cumulative registered and active users"
        type="line"
        data={{
            labels: MONTH_LABELS_ALL,
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
                x: { type: "timeseries", min: timeSeriesMin },
                y: { ticks: { callback: tickCompact } },
            },
            interaction: { mode: "index" },
            plugins: { legend: { display: true } },
        }}
        tall>
        <strong>Registered users</strong> (shaded area) completed the signup process.
        <strong>Active users</strong> (lines) made at least one post or comment on the given site.
        <strong>User ID numbers</strong> (not shown) are much higher, because the site allocates an ID before signup is completed.
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
                x: { stacked: true, type: "timeseries", min: timeSeriesMin },
                y: { stacked: true, max: 1, ticks: { format: PERCENT_OPTIONS } },
            },
            interaction: { mode: "index" },
            plugins: { legend: { display: true } },
        }}
        tall>
        User account age at time of posting or commenting.
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
                x: { stacked: true, type: "timeseries", min: timeSeriesMin },
                y: { stacked: false, max: 0.6, ticks: { format: PERCENT_OPTIONS } },
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
                x: { stacked: true, type: "timeseries", min: timeSeriesMin },
                y: { stacked: false, max: 0.7, ticks: { format: PERCENT_OPTIONS } },
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
                x: { type: "timeseries", min: timeSeriesMin },
                y: { ticks: { callback: tickCompact } },
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
                x: { type: "timeseries", min: timeSeriesMin },
                y: { ticks: { callback: tickCompact } },
            },
            plugins: { tooltip: { callbacks: { footer: tooltipPerDay } } },
        }} />
    <ChartComponent
        title="Posts per active user"
        type="line"
        data={{
            labels: monthLabelsSite,
            datasets: [
                {
                    label: "Posts per active user",
                    data: json[data.site].posts.map((v, i) => v / activeUsers[i]),
                    borderColor: COLORS.posts,
                },
            ],
        }}
        options={{
            scales: { x: { type: "timeseries", min: Math.max(timeSeriesMin, new Date(2001, 0, 1).getTime()) } },
        }}>
        1999 and 2000 are excluded so later years are readable. September 1999 saw 20 posts per active user.
    </ChartComponent>
    <ChartComponent
        title="Comments per active user"
        type="line"
        data={{
            labels: monthLabelsSite,
            datasets: [
                {
                    label: "Comments per active user",
                    data: json[data.site].comments.map((v, i) => v / activeUsers[i]),
                    borderColor: COLORS.comments,
                },
            ],
        }}
        options={{
            scales: { x: { type: "timeseries", min: timeSeriesMin } },
        }} />
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
                        (v, i) => v / (data.site === "all" ? POSTS_EXCLUDING_ASK : json[data.site].posts)[i]
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
                            "Deleted: " + NUMBER_FORMAT.format(json[data.site].posts_deleted[dataIndex]),
                            data.site === "all"
                                ? "Total (ex AskMe): " + NUMBER_FORMAT.format(POSTS_EXCLUDING_ASK[dataIndex])
                                : "Total: " + NUMBER_FORMAT.format(json[data.site].posts[dataIndex]),
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
                    data: json[data.site].posts_weekdays_percent.map((y, i) => ({ x: i, y })),
                    backgroundColor: COLORS.posts,
                },
                {
                    label: "Comments",
                    data: json[data.site].comments_weekdays_percent.map((y, i) => ({ x: i, y })),
                    backgroundColor: COLORS.comments,
                },
            ],
        }}
        options={{
            datasets: { bar: { categoryPercentage: 0.9, barPercentage: 1 } },
            scales: { y: { max: 0.2, ticks: { format: PERCENT_OPTIONS } } },
            interaction: { mode: "index" },
            plugins: { legend: { display: true } },
        }}>
        Timestamps are recorded on the MetaFilter server in Pacific Time. This chart can't be filtered by time period.
    </ChartComponent>
    <ChartComponent
        title="Posts and comments by hour"
        type="bar"
        data={{
            labels: Array.from({ length: 24 }, (_, i) => HOUR_FORMAT.format(i * 60 * 60 * 1000)),
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
            scales: { y: { max: 0.07, ticks: { format: PERCENT_OPTIONS } } },
            interaction: { mode: "index" },
            plugins: { legend: { display: true } },
        }}>
        Timestamps are recorded on the MetaFilter server in Pacific Time. This chart can't be filtered by time period.
    </ChartComponent>
</div>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<menu
    class="fixed right-0 top-0 z-50 h-screen max-w-[90vw] overflow-y-auto border-mefi-blue bg-white p-4 text-lg transition-transform duration-300 ease-in-out"
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
            {#each document.querySelectorAll("h2:not(.menu-ignore), h3") as h}
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
        @apply select-none font-black;
    }

    h2 {
        @apply mb-2 bg-mefi-paler px-2 py-1 text-base uppercase tracking-[0.15em] text-mefi-blue sm:px-4;
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
