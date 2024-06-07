<script lang="ts">
    import { toAnchor } from "$lib/util"
    export let text: string
</script>

<h3 id={toAnchor(text)} class="mt-8 scroll-mt-[96px] text-xl text-mefi-blue sm:text-2xl">
    {text} <a href="#{toAnchor(text)}" class="text-lg font-black text-mefi-pale hover:text-mefi-blue">#</a>
</h3>
