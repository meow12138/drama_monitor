<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const isCollapsed = ref(false)
const mobileOpen = ref(false)

const activeMenu = computed(() => route.path)

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
}

function closeMobile() {
  mobileOpen.value = false
}

const menuItems = [
  { path: '/', title: '监控首页', icon: 'DataLine' },
]
</script>

<template>
  <div class="layout-wrapper">
    <!-- Mobile overlay -->
    <div v-if="mobileOpen" class="mobile-overlay" @click="closeMobile"></div>

    <!-- Sider -->
    <aside class="sider" :class="{ collapsed: isCollapsed, 'mobile-open': mobileOpen }">
      <!-- Logo -->
      <div class="logo">
        <div class="logo-icon">
          <el-icon size="20" color="#00BF8A"><VideoPlay /></el-icon>
        </div>
        <span v-show="!isCollapsed || mobileOpen" class="logo-text">短剧监控</span>
      </div>

      <!-- Menu -->
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapsed && !mobileOpen"
        :collapse-transition="false"
        :unique-opened="true"
        router
      >
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <el-icon>
            <component :is="item.icon" />
          </el-icon>
          <template #title>{{ item.title }}</template>
        </el-menu-item>
      </el-menu>

      <!-- Collapse button -->
      <div class="collapse-btn" @click="mobileOpen ? closeMobile() : toggleCollapse()">
        <span v-if="!isCollapsed && !mobileOpen" class="collapse-icon">&#8801;</span>
        <el-icon v-else-if="isCollapsed && !mobileOpen" :size="16"><Expand /></el-icon>
        <el-icon v-else :size="16"><Close /></el-icon>
      </div>
    </aside>

    <!-- Main -->
    <div class="main" :class="{ collapsed: isCollapsed }">
      <!-- Header -->
      <header class="header">
        <div class="header-left">
          <el-button
            v-if="!mobileOpen"
            class="mobile-menu-btn"
            text
            @click="mobileOpen = true"
          >
            <el-icon :size="18"><Fold /></el-icon>
          </el-button>
        </div>
        <div class="header-right">
          <span class="header-version">海外短剧爆款监控</span>
        </div>
      </header>

      <!-- Content -->
      <main class="content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.layout-wrapper {
  min-height: 100vh;
}

/* Sider */
.sider {
  position: fixed;
  top: 0;
  left: 0;
  width: var(--zw-sider-width);
  height: 100vh;
  background: #ffffff;
  border-right: 1px solid var(--zw-border);
  display: flex;
  flex-direction: column;
  z-index: 200;
  transition: width 0.3s, transform 0.3s;
  overflow: hidden;
}

.sider.collapsed {
  width: var(--zw-sider-collapsed-width);
}

/* Logo */
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  flex-shrink: 0;
  padding: 0 16px;
}

.logo-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #e6f9f3;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: var(--zw-text);
  white-space: nowrap;
}

/* Menu */
:deep(.el-menu) {
  flex: 1;
  border-right: none !important;
  background: transparent;
  overflow-y: auto;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  height: 46px;
  line-height: 46px;
  border-radius: 4px;
  margin: 2px 8px;
  width: calc(100% - 16px);
  color: #4e5969 !important;
  font-size: 14px;
  transition: background-color 0.15s, color 0.15s;
}

:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  background-color: rgba(0, 0, 0, 0.04) !important;
  color: var(--zw-text) !important;
}

/* Active leaf */
:deep(.el-menu-item.is-active) {
  background-color: var(--zw-primary-bg) !important;
  color: var(--zw-primary) !important;
  font-weight: 600;
}

:deep(.el-menu-item.is-active::after) {
  display: none !important;
}

/* Active parent */
:deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  color: var(--zw-primary) !important;
  font-weight: 600;
  background-color: transparent !important;
}

:deep(.el-sub-menu.is-active > .el-sub-menu__title .el-icon) {
  color: var(--zw-primary) !important;
}

/* Collapse button */
.collapse-btn {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 16px;
  background: #f7f8fa;
  border-top: 1px solid var(--zw-border);
  cursor: pointer;
  color: var(--zw-text-secondary);
  flex-shrink: 0;
}

.collapse-btn:hover {
  color: var(--zw-primary);
}

.collapse-icon {
  font-size: 18px;
  line-height: 1;
  font-weight: 400;
  letter-spacing: -1px;
}

/* Collapsed state adjustments */
.sider.collapsed .logo {
  padding: 0;
}

.sider.collapsed :deep(.el-menu-item),
.sider.collapsed :deep(.el-sub-menu__title) {
  margin: 2px 0;
  width: 100%;
  padding: 0 !important;
  justify-content: center;
}

/* Main area */
.main {
  margin-left: var(--zw-sider-width);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  transition: margin-left 0.3s;
}

.main.collapsed {
  margin-left: var(--zw-sider-collapsed-width);
}

/* Header */
.header {
  height: var(--zw-header-height);
  position: sticky;
  top: 0;
  z-index: 100;
  background: #ffffff;
  border-bottom: 1px solid var(--zw-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
}

.header-left {
  display: flex;
  align-items: center;
}

.mobile-menu-btn {
  display: none;
}

.header-version {
  font-size: 13px;
  color: var(--zw-text-secondary);
}

/* Content */
.content {
  flex: 1;
  padding: var(--zw-gap);
  background: var(--zw-bg);
  overflow-y: auto;
}

/* Mobile overlay */
.mobile-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 199;
}

/* Responsive */
@media (max-width: 768px) {
  .sider {
    transform: translateX(-100%);
  }

  .sider.mobile-open {
    transform: translateX(0);
  }

  .sider.collapsed {
    width: var(--zw-sider-width);
  }

  .main {
    margin-left: 0;
  }

  .mobile-menu-btn {
    display: inline-flex;
  }
}
</style>
