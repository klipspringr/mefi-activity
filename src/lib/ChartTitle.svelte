<script lang="ts">
    export let text: string

    const anchor = text.trim().toLowerCase().replace(/\W/g, "_")
</script>

<h3 id={anchor} class="scroll-mt-[94px] text-xl text-mefi-blue sm:text-2xl">
    {text} <a href="#{anchor}" class="text-lg font-black text-mefi-pale hover:text-mefi-blue">#</a>
</h3>
