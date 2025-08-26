import { browser } from "$app/environment"
import { isSite, isPeriod, type TPeriod, type TSite } from "$lib/common"
import type { PageLoad } from "./$types"

export const load: PageLoad = ({ url }) => {
    let site: TSite = "all"
    let period: TPeriod = "all"

    if (browser) {
        const paramSite = url.searchParams.get("site")
        if (paramSite && isSite(paramSite)) site = paramSite

        const paramTime = url.searchParams.get("time")
        if (paramTime && isPeriod(paramTime)) period = paramTime
    }

    return { site, period }
}
