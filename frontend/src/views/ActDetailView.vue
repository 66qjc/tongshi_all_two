<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getShowcase } from '../api/showcase'
import type { ShowcaseItemOut, ContentBlock } from '../api/showcase'
import { resolveFileUrl } from '../utils/url'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const loadError = ref(false)
const item = ref<ShowcaseItemOut | null>(null)

const sectionLabels: Record<string, string> = {
  welfare: '公益课',
  reading_club: '读书会',
}

const sectionLabel = computed(() => (item.value ? sectionLabels[item.value.section] || '行动内容' : '行动内容'))
const coverUrl = computed(() => resolveFileUrl(item.value?.cover_url))

const imageUrls = computed(() => {
  if (!item.value) return []
  return item.value.images
    .map(image => resolveFileUrl(image.url))
    .filter(Boolean)
})

// 是否有图文混排内容块；有则优先按块顺序渲染，否则回退到旧版纯文本 + 图片网格
const hasContentBlocks = computed(() =>
  item.value?.content_blocks !== undefined && item.value.content_blocks.length > 0
)

const getBlockImageUrl = (fileId?: number) => fileId ? resolveFileUrl(`/api/files/${fileId}`) : ''

const renderableBlocks = computed(() => {
  if (!item.value?.content_blocks) return []
  return item.value.content_blocks.filter((b: ContentBlock) => {
    if (b.type === 'text') return !!b.data.text?.trim()
    if (b.type === 'image') return !!b.data.file_id
    return false
  })
})

onMounted(async () => {
  loading.value = true
  loadError.value = false
  try {
    const data = await getShowcase()
    const targetId = Number(route.params.id)
    const allItems = Object.values(data || {}).flat()
    item.value = allItems.find(entry => entry.id === targetId) || null
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="act-detail-page">
    <section class="detail-hero">
      <div class="container">
        <button class="back-link" type="button" @click="router.push('/act')">返回行页面</button>

        <div v-if="loading" class="detail-state">内容加载中...</div>
        <div v-else-if="loadError" class="detail-state detail-error">
          内容加载失败，请刷新页面重试。
        </div>
        <div v-else-if="!item" class="detail-state">
          未找到对应的行动内容。
        </div>

        <article v-else class="detail-article">
          <div class="article-header">
            <span class="section-kicker">{{ sectionLabel }}</span>
            <h1>{{ item.title }}</h1>
          </div>

          <div v-if="coverUrl" class="cover-frame">
            <img :src="coverUrl" :alt="item.title" />
          </div>

          <!-- 图文混排优先：按 content_blocks 顺序渲染段落与图片 -->
          <section v-if="hasContentBlocks && renderableBlocks.length > 0" class="article-blocks">
            <div
              v-for="(block, index) in renderableBlocks"
              :key="`block-${item.id}-${index}`"
              class="article-block"
            >
              <p v-if="block.type === 'text'" class="block-text">{{ block.data.text }}</p>
              <figure v-else-if="block.type === 'image'" class="block-figure">
                <a
                  :href="getBlockImageUrl(block.data.file_id)"
                  target="_blank"
                  rel="noopener"
                  class="block-image-link"
                >
                  <img
                    :src="getBlockImageUrl(block.data.file_id)"
                    :alt="block.data.caption || `${item.title} 图片 ${index + 1}`"
                  />
                </a>
                <figcaption v-if="block.data.caption">{{ block.data.caption }}</figcaption>
              </figure>
            </div>
          </section>

          <!-- 旧版回退：纯文本 + 图片网格 -->
          <div v-else class="article-content">
            <p v-if="item.content" class="full-content">{{ item.content }}</p>
            <p v-else>当前内容暂未填写正文。</p>
          </div>

          <section v-if="!hasContentBlocks && item.images.length > 0" class="image-section">
            <div class="section-title">
              <span>相关图片</span>
              <small>{{ imageUrls.length }} 张</small>
            </div>
            <div class="image-grid">
              <a
                v-for="(image, index) in imageUrls"
                :key="`${image}-${index}`"
                :href="image"
                target="_blank"
                rel="noopener"
                class="image-card"
              >
                <img :src="image" :alt="`${item.title} 图片 ${index + 1}`" />
              </a>
            </div>
          </section>

          <section v-if="item.link_url" class="more-section">
            <div>
              <span class="section-kicker">了解更多</span>
              <h2>继续查看相关内容</h2>
              <p>点击下方按钮，将在新窗口打开原始页面。</p>
            </div>
            <a :href="item.link_url" target="_blank" rel="noopener" class="more-link">
              了解更多
            </a>
          </section>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.act-detail-page {
  min-height: 100vh;
  padding-top: 60px;
  background: var(--color-bg);
}

.detail-hero {
  padding: var(--space-2xl) 0 var(--space-3xl);
}

.back-link {
  display: inline-flex;
  margin-bottom: var(--space-xl);
  padding: 0;
  color: var(--color-act);
  background: transparent;
  border: 0;
  font-family: inherit;
  font-size: 0.86rem;
  font-weight: 700;
  cursor: pointer;
}

.back-link:hover {
  opacity: 0.75;
}

.detail-state {
  padding: var(--space-3xl) var(--space-xl);
  color: var(--color-text-secondary);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  text-align: center;
}

.detail-error {
  color: #c0392b;
}

.detail-article {
  max-width: 960px;
  margin: 0 auto;
}

.article-header {
  margin-bottom: var(--space-xl);
}

.section-kicker {
  display: inline-block;
  margin-bottom: var(--space-xs);
  color: var(--color-act);
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.article-header h1 {
  max-width: 820px;
  color: var(--color-text);
  font-family: var(--font-serif);
  font-size: 2rem;
  font-weight: 900;
  line-height: 1.35;
  letter-spacing: 0.03em;
}

.cover-frame {
  overflow: hidden;
  margin-bottom: var(--space-xl);
  background: var(--color-act-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  aspect-ratio: 16 / 9;
}

.cover-frame img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.article-content {
  padding: var(--space-xl);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.article-content p {
  color: var(--color-text-secondary);
  font-size: 0.96rem;
  line-height: 1.9;
}

.full-content {
  white-space: pre-line;
}

.image-section,
.more-section {
  margin-top: var(--space-xl);
}

.section-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: var(--space-md);
}

.section-title span {
  color: var(--color-text);
  font-family: var(--font-serif);
  font-size: 1.1rem;
  font-weight: 700;
}

.section-title small {
  color: var(--color-text-muted);
  font-size: 0.82rem;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-md);
}

.image-card {
  display: block;
  overflow: hidden;
  background: var(--color-act-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  aspect-ratio: 16 / 10;
}

.image-card img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform var(--duration-normal) var(--ease-out);
}

.image-card:hover img {
  transform: scale(1.03);
}

.more-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-xl);
  padding: var(--space-xl);
  background: var(--color-act-bg);
  border: 1px solid rgba(58, 125, 92, 0.14);
  border-radius: var(--radius-md);
}

.more-section h2 {
  margin-bottom: var(--space-xs);
  color: var(--color-text);
  font-family: var(--font-serif);
  font-size: 1.08rem;
  font-weight: 700;
}

.more-section p {
  color: var(--color-text-secondary);
  font-size: 0.86rem;
}

.more-link {
  flex-shrink: 0;
  padding: 0.55rem 1rem;
  color: var(--color-bg-card);
  background: var(--color-act);
  border-radius: var(--radius-sm);
  font-size: 0.88rem;
  font-weight: 700;
}

.more-link:hover {
  opacity: 0.9;
}

@media (max-width: 768px) {
  .detail-hero {
    padding-top: var(--space-xl);
  }

  .article-header h1 {
    font-size: 1.45rem;
  }

  .article-content {
    padding: var(--space-lg);
  }

  .image-grid {
    grid-template-columns: 1fr;
  }

  .more-section {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>

.article-blocks {
  padding: var(--space-xl);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.article-block + .article-block {
  margin-top: var(--space-lg);
}

.block-text {
  color: var(--color-text-secondary);
  font-size: 0.96rem;
  line-height: 1.9;
  white-space: pre-line;
}

.block-figure {
  margin: 0;
}

.block-image-link {
  display: block;
  overflow: hidden;
  border-radius: var(--radius-md);
  background: var(--color-act-bg);
}

.block-image-link img {
  display: block;
  width: 100%;
  height: auto;
  max-height: 560px;
  object-fit: contain;
}

.block-figure figcaption {
  margin-top: var(--space-sm);
  color: var(--color-text-muted);
  font-size: 0.82rem;
  text-align: center;
}