<script lang="ts">
    import {
        Chart,
        type BubbleDataPoint,
        type ChartData,
        type ChartOptions,
        type ChartTypeRegistry,
        type Plugin,
        type Point,
    } from "chart.js"
    import "chartjs-adapter-date-fns"
    import { onMount, type Snippet } from "svelte"

    let {
        title,
        titleForAnchor,
        type,
        data,
        options,
        plugins = [],
        tall = false,
        children,
    }: {
        title: string
        titleForAnchor?: string
        type: keyof ChartTypeRegistry
        data: ChartData<typeof type, (number | [number, number] | Point | BubbleDataPoint | null)[], unknown>
        options: ChartOptions<typeof type>
        plugins?: Plugin<typeof type>[]
        tall?: boolean
        children?: Snippet
    } = $props()

    let chart: Chart
    let canvasElement: HTMLCanvasElement

    let anchor = $derived((titleForAnchor || title).trim().toLowerCase().replace(/\W/g, "_"))

    onMount(() => {
        chart = new Chart(canvasElement, { type, data, options, plugins })
        return () => chart?.destroy()
    })

    $effect(() => {
        chart.data = data
        chart.options = options
        chart.update()
    })
</script>

<div class="mb-8 px-2 sm:px-4">
    <h3 id={anchor} class="scroll-mt-[94px] text-xl text-mefi-blue sm:text-2xl">
        {title} <a href="#{anchor}" class="select-none text-lg font-black text-mefi-pale hover:text-mefi-blue">#</a>
    </h3>
    <div class="relative {tall ? 'h-[70vw] sm:h-[50vw]' : 'h-[60vw] sm:h-[50vw]'} sm:max-h-[640px]">
        <canvas bind:this={canvasElement}></canvas>
    </div>
    {#if children}
        <div class="mt-2 grid grid-cols-[auto_1fr] gap-x-2 text-sm sm:text-base">
            <div class="select-none bg-mefi-paler p-1 text-xs font-black uppercase tracking-wider text-mefi-blue">
                Note
            </div>
            <div>
                {@render children()}
            </div>
        </div>
    {/if}
</div>
