import type { ClientInit } from "@sveltejs/kit"
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

export const init: ClientInit = () => {
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
    Chart.defaults.scales.timeseries.ticks.callback = (v) => {
        const d = new Date(v)
        return d.getMonth() == 6 ? d.getFullYear() : undefined
    }

    // these lines cause the gridlines glitch
    // we work around the glitch by letting $effect call update() after initialising (which would otherwise be unnecessary)
    Chart.defaults.scales.linear.grid = { z: 1 }
    Chart.defaults.scales.timeseries.grid = { z: 1 }

    Chart.defaults.plugins.legend.display = false
    Chart.defaults.plugins.legend.position = "bottom"
    Chart.defaults.plugins.legend.onClick = () => {}

    Tooltip.positioners.cursor = (_: ActiveElement[], eventPos: Point) => eventPos
    Chart.defaults.plugins.tooltip.position = "cursor"
}
