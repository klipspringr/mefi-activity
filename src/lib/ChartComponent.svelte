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
    import { onMount, type Snippet } from "svelte"

    interface Props {
        title: string
        type: keyof ChartTypeRegistry
        data: ChartData<typeof type, (number | [number, number] | Point | BubbleDataPoint | null)[], unknown>
        options: ChartOptions<typeof type>
        plugins?: Plugin<typeof type>[]
        tall?: boolean
        children?: Snippet
    }

    let { title, type, data, options, plugins = [], tall = false, children }: Props = $props()

    let chart: Chart
    let canvasElement: HTMLCanvasElement

    let anchor = $derived(title.trim().toLowerCase().replace(/\W/g, "_"))

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
        {title} <a href="#{anchor}" class="text-lg font-black text-mefi-pale hover:text-mefi-blue">#</a>
    </h3>
    <div class="relative {tall ? 'h-[70vw] sm:h-[50vw]' : 'h-[60vw] sm:h-[50vw]'} sm:max-h-[640px]">
        <canvas bind:this={canvasElement}></canvas>
    </div>
    {#if children}
        <div class="note mt-2 text-sm sm:text-base">
            {@render children()}
        </div>
    {/if}
</div>

<style type="postcss">
    .note::before {
        @apply mr-1 bg-mefi-paler px-1.5 py-0.5 text-xs font-black uppercase text-mefi-blue content-['Note'];
    }
</style>
