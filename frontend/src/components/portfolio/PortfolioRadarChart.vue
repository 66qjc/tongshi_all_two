<script setup lang="ts">
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([RadarChart, TooltipComponent, LegendComponent, CanvasRenderer])

defineProps<{
  option: Record<string, unknown>
}>()
</script>

<template>
  <v-chart :option="option" class="portfolio-radar-chart" autoresize />
</template>

<style scoped>
.portfolio-radar-chart {
  width: 100%;
  height: 360px;
}
</style>
