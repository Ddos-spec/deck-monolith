import {
  BOS_RATINGS_STORAGE_KEY,
  DECK_CATEGORIES,
  buildAiPromptFromDeck,
  type BosRatingRecord,
  type BosTier,
  type DeckItem,
} from "../lib/deckCatalog";

type QuickMode = "all" | "morph" | "animated" | "graded" | "top-tier";
type SortMode = "default" | "slides-desc" | "morph-desc" | "rating-desc";
type FxMode = "morph" | "kinetic" | "spatial" | "wipe";
type ArrowMode = "slide" | "deck";
type ViewMode = "bento" | "grid" | "list";

interface GalleryState {
  search: string;
  categories: Set<string>;
  industries: Set<string>;
  quickMode: QuickMode;
  sortMode: SortMode;
  viewMode: ViewMode;
  activePane: "category" | "industry";
  activeDeckSlug: string | null;
  activeSlideIndex: number;
  pageLimit: number;
  fxMode: FxMode;
  arrowMode: ArrowMode;
  heroSlug: string;
  heroSlideIdx: number;
  heroAutoPlay: boolean;
}

function esc(val: unknown): string {
  return String(val ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function loadRatings(): Record<string, BosRatingRecord> {
  try {
    const raw = localStorage.getItem(BOS_RATINGS_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

export function saveRatings(ratings: Record<string, BosRatingRecord>): void {
  try {
    localStorage.setItem(BOS_RATINGS_STORAGE_KEY, JSON.stringify(ratings));
  } catch {
    // Ignore storage quota errors gracefully
  }
}

export function showToast(message: string): void {
  const toast = document.getElementById("vault-toast");
  const text = document.getElementById("vault-toast-text");
  if (!toast || !text) return;
  text.textContent = message;
  toast.classList.remove("opacity-0", "translate-y-2");
  toast.classList.add("opacity-100", "translate-y-0");
  window.clearTimeout((toast as HTMLElement & { _timer?: number })._timer);
  (toast as HTMLElement & { _timer?: number })._timer = window.setTimeout(() => {
    toast.classList.add("opacity-0", "translate-y-2");
    toast.classList.remove("opacity-100", "translate-y-0");
  }, 1900);
}

export async function copyToClipboard(value: string, label: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(value);
    showToast(label);
  } catch {
    const ta = document.createElement("textarea");
    ta.value = value;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
    showToast(label);
  }
}

export function exportRatingsJson(decks: DeckItem[]): void {
  const ratings = loadRatings();
  const entries = Object.values(ratings);
  const payload = {
    exportedAt: new Date().toISOString(),
    source: "DECK.VAULT — Bos Ratings",
    totalDecksInCatalog: decks.length,
    totalGraded: entries.length,
    ratings: entries,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `bos-deck-ratings-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast(`Exported ${entries.length} Bos ratings`);
}

function tierBadgeClass(tier: BosTier | null): string {
  switch (tier) {
    case "S":
      return "bg-emerald-500/20 text-emerald-300 border border-emerald-400/40";
    case "A":
      return "bg-violet-500/20 text-violet-300 border border-violet-400/40";
    case "B":
      return "bg-amber-500/20 text-amber-300 border border-amber-400/40";
    case "C":
      return "bg-zinc-500/20 text-zinc-300 border border-zinc-400/40";
    default:
      return "bg-zinc-800 text-zinc-400";
  }
}

export function initDeckGallery(decks: DeckItem[]): void {
  const deckBySlug = new Map<string, DeckItem>(decks.map((d) => [d.slug, d]));

  const savedView = (() => {
    try {
      const v = localStorage.getItem("deck-vault-view");
      return v === "grid" || v === "list" || v === "bento" ? v : "bento";
    } catch {
      return "bento";
    }
  })();

  const state: GalleryState = {
    search: "",
    categories: new Set<string>(),
    industries: new Set<string>(),
    quickMode: "all",
    sortMode: "default",
    viewMode: savedView,
    activePane: "category",
    activeDeckSlug: null,
    activeSlideIndex: 0,
    pageLimit: 24,
    fxMode: "morph",
    arrowMode: "slide",
    heroSlug: decks[0]?.slug ?? "",
    heroSlideIdx: 0,
    heroAutoPlay: true,
  };

  let ratings = loadRatings();
  let autoPlayTimer: number | null = null;
  let renderedSignature = "";

  // DOM Elements
  const grid = document.getElementById("deck-grid");
  const emptyState = document.getElementById("deck-empty-state");
  const resultCountEl = document.getElementById("gallery-result-count");
  const searchInput = document.getElementById("deck-search-input") as HTMLInputElement | null;
  const sortSelect = document.getElementById("deck-sort-select") as HTMLSelectElement | null;
  const activeChipsContainer = document.getElementById("active-filter-chips");
  const loadMoreWrap = document.getElementById("load-more-wrap");
  const loadMoreBtn = document.getElementById("load-more-decks-btn");
  const loadMoreCaption = document.getElementById("load-more-caption");
  const sentinelEl = document.getElementById("infinite-scroll-sentinel");

  // Theme & Telemetry HUD Elements
  const themeToggleBtn = document.getElementById("theme-toggle-btn");
  const themeToggleLabel = document.getElementById("theme-toggle-label");
  const themeToggleDot = document.getElementById("theme-toggle-dot");
  const hudCursorXy = document.getElementById("hud-cursor-xy");
  const hudScrollPct = document.getElementById("hud-scroll-pct");
  const awwwardsCursor = document.getElementById("awwwards-cursor");

  // Hero Stage Elements
  const heroTitleEl = document.getElementById("hero-stage-title");
  const heroCounterEl = document.getElementById("hero-stage-slide-counter");
  const heroImgActive = document.getElementById("hero-stage-img-active") as HTMLImageElement | null;
  const heroImgPrev = document.getElementById("hero-stage-img-prev") as HTMLImageElement | null;
  const heroDownloadBtn = document.getElementById("hero-download-btn") as HTMLAnchorElement | null;
  const heroThumbStrip = document.getElementById("hero-thumb-strip");
  const heroOpenViewerBtn = document.getElementById("hero-open-viewer-btn");
  const heroRandomBtn = document.getElementById("hero-random-deck-btn");
  const heroAutoPlayBtn = document.getElementById("hero-autoplay-stage-btn");
  const heroAutoPlayStatus = document.getElementById("hero-autoplay-status");

  // Filter Modal Elements
  const filterBackdrop = document.getElementById("filter-modal-backdrop");
  const filterPanel = document.getElementById("filter-modal-panel");
  const filterSearch = document.getElementById("filter-modal-search") as HTMLInputElement | null;
  const filterBadge = document.getElementById("filter-active-badge");
  const filterMatchLabel = document.getElementById("filter-modal-match-label");

  // Scoreboard Elements
  const scoreboardBackdrop = document.getElementById("scoreboard-backdrop");
  const scoreboardPanel = document.getElementById("scoreboard-panel");

  // Viewer Modal Elements
  const viewerBackdrop = document.getElementById("deck-viewer-backdrop");
  const viewerPanel = document.getElementById("deck-viewer-panel");
  const viewerTitle = document.getElementById("viewer-deck-title");
  const viewerMetaPills = document.getElementById("viewer-meta-pills");
  const viewerPermalink = document.getElementById("viewer-permalink-link") as HTMLAnchorElement | null;
  const viewerDownloadBtn = document.getElementById("viewer-download-pptx-btn") as HTMLAnchorElement | null;
  const viewerActiveImg = document.getElementById("viewer-active-slide-img") as HTMLImageElement | null;
  const viewerPrevBufferImg = document.getElementById("viewer-prev-slide-img") as HTMLImageElement | null;
  const viewerStageFrame = document.getElementById("viewer-stage-frame");
  const viewerSlideCounter = document.getElementById("viewer-slide-counter");
  const viewerThumbStrip = document.getElementById("viewer-thumbnail-strip");
  const viewerPrevBtn = document.getElementById("viewer-prev-slide-btn") as HTMLButtonElement | null;
  const viewerNextBtn = document.getElementById("viewer-next-slide-btn") as HTMLButtonElement | null;
  const viewerPrevDeckBtn = document.getElementById("viewer-prev-deck-btn") as HTMLButtonElement | null;
  const viewerNextDeckBtn = document.getElementById("viewer-next-deck-btn") as HTMLButtonElement | null;
  const viewerDeckPosition = document.getElementById("viewer-deck-position");
  const viewerArrowModeBtn = document.getElementById("viewer-arrow-mode-btn");
  const viewerArrowModeLabel = document.getElementById("viewer-arrow-mode-label");
  const viewerAutoPlayBtn = document.getElementById("viewer-autoplay-btn");
  const viewerAutoPlayIcon = document.getElementById("viewer-autoplay-icon");
  const viewerAutoPlayLabel = document.getElementById("viewer-autoplay-label");
  const viewerReplayFxBtn = document.getElementById("viewer-replay-fx-btn");
  const fxLiveRule = document.getElementById("fx-live-rule");
  const fxLivePrism = document.getElementById("fx-live-prism");
  const fxLiveNum = document.getElementById("fx-live-num");
  const fxLiveProgress = document.getElementById("fx-live-progress");
  const bosAutoNextToggle = document.getElementById("bos-auto-next-toggle") as HTMLInputElement | null;
  const bosNextUnreviewedBtn = document.getElementById("bos-next-unreviewed-btn");
  const viewerDescription = document.getElementById("viewer-deck-description");
  const viewerTags = document.getElementById("viewer-deck-tags");
  const viewerSwatches = document.getElementById("viewer-color-swatches");
  const viewerFonts = document.getElementById("viewer-font-pills");
  const viewerOoxmlGrid = document.getElementById("viewer-ooxml-grid");
  const viewerBlueprintSummary = document.getElementById("viewer-blueprint-summary");
  const bosNotesInput = document.getElementById("bos-review-notes") as HTMLTextAreaElement | null;
  const bosSavedStatus = document.getElementById("bos-grade-saved-status");

  // --- Theme & Scroll Telemetry ---
  function syncThemeUi(): void {
    const isObsidian = document.documentElement.classList.contains("theme-obsidian");
    if (themeToggleLabel) themeToggleLabel.textContent = isObsidian ? "LIMESTONE" : "DARK ROOM";
    if (themeToggleDot) {
      themeToggleDot.className = isObsidian
        ? "h-2.5 w-2.5 border border-[var(--brut-border-strong)] bg-[#F2EFE9]"
        : "h-2.5 w-2.5 border border-[var(--brut-border-strong)] bg-[#111111]";
    }
  }
  syncThemeUi();

  themeToggleBtn?.addEventListener("click", () => {
    const isObsidian = document.documentElement.classList.toggle("theme-obsidian");
    try {
      localStorage.setItem("deck-vault-theme", isObsidian ? "obsidian" : "limestone");
    } catch {}
    syncThemeUi();
    showToast(isObsidian ? "Theme: Obsidian Monolith" : "Theme: Raw Limestone Concrete");
  });

  // Single-rAF Telemetry Cursor & Smooth Card 3D Tilt
  let pendingPtrX = 0;
  let pendingPtrY = 0;
  let ptrDirty = false;
  let tiltedCard: HTMLElement | null = null;

  function flushCursorRaf(): void {
    ptrDirty = false;
    if (hudCursorXy) {
      const px = String(Math.round(pendingPtrX)).padStart(4, "0");
      const py = String(Math.round(pendingPtrY)).padStart(4, "0");
      hudCursorXy.textContent = `POS ${px}·${py}`;
    }
    if (awwwardsCursor) {
      awwwardsCursor.style.transform = `translate3d(${pendingPtrX}px, ${pendingPtrY}px, 0) translate(-50%, -50%)`;
      awwwardsCursor.style.opacity = "0.75";
    }
    if (tiltedCard) {
      const rect = tiltedCard.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) {
        const nx = (pendingPtrX - rect.left) / rect.width - 0.5;
        const ny = (pendingPtrY - rect.top) / rect.height - 0.5;
        tiltedCard.style.setProperty("--card-rx", `${(-ny * 4.5).toFixed(2)}deg`);
        tiltedCard.style.setProperty("--card-ry", `${(nx * 5.0).toFixed(2)}deg`);
      }
    }
  }

  window.addEventListener(
    "pointermove",
    (e) => {
      pendingPtrX = e.clientX;
      pendingPtrY = e.clientY;
      const under = (e.target as HTMLElement | null)?.closest<HTMLElement>(".deck-card") ?? null;
      if (tiltedCard && tiltedCard !== under) {
        tiltedCard.style.setProperty("--card-rx", "0deg");
        tiltedCard.style.setProperty("--card-ry", "0deg");
      }
      tiltedCard = state.viewMode !== "list" ? under : null;
      if (!ptrDirty) {
        ptrDirty = true;
        window.requestAnimationFrame(flushCursorRaf);
      }
    },
    { passive: true }
  );

  window.addEventListener(
    "scroll",
    () => {
      if (!hudScrollPct) return;
      const doc = document.documentElement;
      const maxScroll = Math.max(1, doc.scrollHeight - window.innerHeight);
      const pct = Math.min(100, Math.max(0, Math.round((window.scrollY / maxScroll) * 100)));
      hudScrollPct.textContent = `${String(pct).padStart(2, "0")}%`;
    },
    { passive: true }
  );

  // --- View Mode Switcher ---
  function syncViewMode(): void {
    if (grid) {
      grid.classList.remove("view-bento", "view-grid", "view-list");
      grid.classList.add(`view-${state.viewMode}`);
    }
    document.querySelectorAll<HTMLButtonElement>("[data-view-mode]").forEach((btn) => {
      const active = btn.dataset.viewMode === state.viewMode;
      btn.classList.toggle("bg-[#C22F10]", active);
      btn.classList.toggle("text-white", active);
      btn.classList.toggle("font-bold", active);
      btn.classList.toggle("font-semibold", !active);
    });
  }
  syncViewMode();

  document.querySelectorAll<HTMLButtonElement>("[data-view-mode]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.viewMode = (btn.dataset.viewMode as ViewMode) || "bento";
      try {
        localStorage.setItem("deck-vault-view", state.viewMode);
      } catch {}
      syncViewMode();
    });
  });

  // --- Hero Live Specimen Stage ---
  function renderHeroSlide(slideIdx: number, animate: boolean = true): void {
    const deck = deckBySlug.get(state.heroSlug) ?? decks[0];
    if (!deck || !heroImgActive) return;
    const slides = deck.slidesPreview.length > 0 ? deck.slidesPreview : [deck.coverImage];
    const clamped = ((slideIdx % slides.length) + slides.length) % slides.length;
    const prevSrc = heroImgActive.getAttribute("src") || "";
    state.heroSlideIdx = clamped;

    heroImgActive.classList.remove("fx-morph-enter");
    heroImgPrev?.classList.remove("fx-morph-leave");
    if (animate && prevSrc && heroImgPrev) {
      heroImgPrev.src = prevSrc;
      heroImgPrev.style.opacity = "1";
      heroImgPrev.classList.add("fx-morph-leave");
    } else if (heroImgPrev) {
      heroImgPrev.style.opacity = "0";
    }

    heroImgActive.src = slides[clamped];
    if (animate) {
      void heroImgActive.offsetWidth;
      heroImgActive.classList.add("fx-morph-enter");
    }
    if (heroCounterEl) {
      heroCounterEl.textContent = `${String(clamped + 1).padStart(2, "0")} / ${slides.length}`;
    }

    heroThumbStrip?.querySelectorAll<HTMLButtonElement>("[data-hero-slide]").forEach((b) => {
      const active = Number(b.dataset.heroSlide) === clamped;
      b.classList.toggle("border-[#FF784E]", active);
      b.classList.toggle("opacity-100", active);
      b.classList.toggle("border-white/10", !active);
      b.classList.toggle("opacity-60", !active);
    });
  }

  function pinHeroDeck(slug: string): void {
    const deck = deckBySlug.get(slug);
    if (!deck) return;
    state.heroSlug = deck.slug;
    state.heroSlideIdx = 0;
    if (heroTitleEl) heroTitleEl.textContent = deck.title;
    if (heroDownloadBtn) heroDownloadBtn.href = deck.pptxUrl;
    if (heroThumbStrip) {
      heroThumbStrip.innerHTML = deck.slidesPreview
        .slice(0, 6)
        .map(
          (src, idx) => `
          <button type="button" data-hero-slide="${idx}" class="aspect-video w-full overflow-hidden rounded border transition-all cursor-pointer ${
            idx === 0 ? "border-[#FF784E] opacity-100" : "border-white/10 opacity-60 hover:opacity-100"
          }">
            <img src="${esc(src)}" alt="Hero keyframe ${idx + 1}" class="h-full w-full object-cover" loading="lazy" />
          </button>`
        )
        .join("");
    }
    renderHeroSlide(0, true);
  }

  heroThumbStrip?.addEventListener("click", (e) => {
    const btn = (e.target as HTMLElement).closest<HTMLButtonElement>("[data-hero-slide]");
    if (btn) renderHeroSlide(Number(btn.dataset.heroSlide ?? 0), true);
  });

  heroOpenViewerBtn?.addEventListener("click", () => {
    if (state.heroSlug) openDeckViewer(state.heroSlug);
  });

  heroRandomBtn?.addEventListener("click", () => {
    const pool = getFilteredSortedDecks();
    const list = pool.length > 0 ? pool : decks;
    if (list.length === 0) return;
    const pick = list[Math.floor(Math.random() * list.length)];
    pinHeroDeck(pick.slug);
    showToast(`Stage pinned: ${pick.title}`);
  });

  heroAutoPlayBtn?.addEventListener("click", () => {
    state.heroAutoPlay = !state.heroAutoPlay;
    if (heroAutoPlayStatus) {
      heroAutoPlayStatus.textContent = state.heroAutoPlay ? "⏸ Live Stage: ON" : "▶ Live Stage: PAUSED";
    }
  });

  window.setInterval(() => {
    if (!state.heroAutoPlay || state.activeDeckSlug !== null || document.hidden) return;
    renderHeroSlide(state.heroSlideIdx + 1, true);
  }, 2400);

  // --- Card Badges & Virtualized DOM Factory ---
  function updateCardGradeBadges(): void {
    document.querySelectorAll<HTMLElement>(".card-bos-grade").forEach((badge) => {
      const deckId = badge.dataset.gradeFor;
      if (!deckId) return;
      const rec = ratings[deckId];
      const tierEl = badge.querySelector(".grade-tier-pill");
      const starsEl = badge.querySelector(".grade-stars-text");
      if (rec && (rec.tier || rec.stars > 0)) {
        badge.classList.remove("hidden");
        badge.classList.add("inline-flex");
        if (tierEl) {
          tierEl.textContent = rec.tier ? `${rec.tier}` : "★";
          tierEl.className = `grade-tier-pill rounded px-1.5 py-0.2 font-mono text-[10px] font-bold ${tierBadgeClass(rec.tier)}`;
        }
        if (starsEl) {
          starsEl.textContent = rec.stars > 0 ? `${"★".repeat(rec.stars)}` : "";
        }
      } else {
        badge.classList.add("hidden");
        badge.classList.remove("inline-flex");
      }
    });
  }

  function buildDeckCardElement(deck: DeckItem, index: number): HTMLElement {
    const specNum = String(index + 1).padStart(4, "0");
    const isFeatured = index % 7 === 0;
    const article = document.createElement("article");
    article.className = "deck-card group relative flex flex-col overflow-hidden" + (isFeatured ? " bento-featured" : "");
    article.dataset.deckId = deck.id;
    article.dataset.deckSlug = deck.slug;
    article.dataset.slidesPreview = JSON.stringify(deck.slidesPreview.slice(0, 6));
    article.dataset.accent = deck.colors[0] ?? "#C22F10";

    const swatches = deck.colors
      .slice(0, 4)
      .map(
        (hex) =>
          `<span class="h-3.5 w-3.5 border border-[var(--brut-border-strong)]" style="background-color:${esc(hex)};" title="${esc(hex)}"></span>`
      )
      .join("");

    article.innerHTML = `
      <button type="button" data-open-deck="${esc(deck.slug)}" class="card-thumb-btn relative block aspect-video w-full overflow-hidden border-b-2 border-[var(--brut-border-strong)] bg-[#111111] text-left focus:outline-none cursor-pointer">
        <img src="${esc(deck.coverImage)}" alt="Inspect ${esc(deck.title)} — Cover Slide" loading="lazy" decoding="async" class="card-preview-img h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.03]" />
        <span aria-hidden="true" class="pointer-events-none absolute left-2 top-2 font-mono text-[10px] font-bold leading-none text-white/70">+</span>
        <span aria-hidden="true" class="pointer-events-none absolute right-2 bottom-2 font-mono text-[10px] font-bold leading-none text-white/70">+</span>
        <div aria-hidden="true" class="pointer-events-none absolute inset-x-0 bottom-0 h-1.5 bg-black/70 opacity-0 transition-opacity duration-200 group-hover:opacity-100">
          <div class="card-hover-progress h-full w-1/6 bg-[#FF784E] transition-all duration-300"></div>
        </div>
        <div aria-hidden="true" class="pointer-events-none absolute inset-x-2.5 top-2.5 flex items-center justify-between gap-2">
          <div class="flex items-center gap-1.5">
            <span class="inline-flex items-center border border-white/25 bg-[#111111]/90 px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider text-[#F2EFE9]">NO. ${specNum}</span>
            ${deck.hasMorph ? `<span class="inline-flex items-center gap-1 border border-[#FF784E]/60 bg-[#111111]/90 px-2 py-0.5 font-mono text-[10px] font-semibold text-[#FFB49A]">✦ MORPH</span>` : ""}
          </div>
          <span class="card-slide-hud inline-flex items-center border border-white/25 bg-[#111111]/90 px-2 py-0.5 font-mono text-[10px] font-bold text-white">${deck.slidesCount} SLIDES</span>
        </div>
        <div aria-hidden="true" class="pointer-events-none absolute inset-x-2.5 bottom-2.5 flex items-center justify-between gap-2">
          <div class="card-bos-grade hidden items-center gap-1.5 border border-white/25 bg-[#111111]/95 px-2 py-0.5 font-mono text-[10px] font-bold text-white" data-grade-for="${esc(deck.id)}">
            <span class="grade-tier-pill px-1 text-[10px]"></span>
            <span class="grade-stars-text text-amber-300"></span>
          </div>
          ${deck.designFamily ? `<span class="ml-auto inline-flex items-center border border-white/20 bg-[#111111]/88 px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider text-zinc-200">${esc(deck.designFamily)}</span>` : ""}
        </div>
      </button>
      <div class="card-meta-wrap flex flex-1 flex-col justify-between gap-3 p-4">
        <div class="min-w-0 flex-1">
          <button type="button" data-open-deck="${esc(deck.slug)}" class="card-title-btn text-left font-display text-[15px] font-bold leading-snug tracking-tight transition-colors hover:text-[#C22F10] focus:outline-none cursor-pointer line-clamp-1">${esc(deck.title)}</button>
          <div class="mt-2.5 flex flex-wrap items-center gap-1.5">
            <span class="brut-chip px-2 py-0.5 font-mono text-[10px] font-bold uppercase">${esc(deck.category)}</span>
            <span class="brut-chip px-2 py-0.5 font-mono text-[10px]">${esc(deck.industry)}</span>
            <div class="ml-auto flex items-center gap-1" title="Extracted Color Palette">${swatches}</div>
          </div>
        </div>
        <div class="card-actions-bar flex items-center justify-between gap-2 border-t border-[var(--brut-border)] pt-3">
          <div class="flex items-center gap-2">
            <button type="button" data-open-deck="${esc(deck.slug)}" class="inline-flex items-center gap-1 font-mono text-[11px] font-bold uppercase tracking-wide transition-colors hover:text-[#C22F10] cursor-pointer whitespace-nowrap">
              <span>Preview</span><span aria-hidden="true">→</span>
            </button>
            <button type="button" data-copy-prompt="${esc(deck.slug)}" title="Copy AI design prompt & OOXML spec for this deck" class="brut-btn hidden sm:inline-flex items-center gap-1 px-2 py-0.5 font-mono text-[10px] font-bold cursor-pointer whitespace-nowrap">⧉ AI Prompt</button>
            <button type="button" data-pin-hero="${esc(deck.slug)}" title="Load onto Featured Hero Stage" class="brut-btn hidden xl:inline-flex items-center px-1.5 py-0.5 font-mono text-[10px] font-bold cursor-pointer">◎</button>
          </div>
          <a href="${esc(deck.pptxUrl)}" download data-download-pptx title="Download ${esc(deck.title)} (.pptx)" class="brut-btn-primary inline-flex shrink-0 items-center gap-1 px-2.5 py-1 font-mono text-[11px] font-bold">
            <span>↓ .PPTX</span>
          </a>
        </div>
      </div>
    `;
    return article;
  }

  function deckMatchesFilters(deck: DeckItem): boolean {
    if (state.categories.size > 0 && !state.categories.has(deck.category)) return false;
    if (state.industries.size > 0 && !state.industries.has(deck.industry)) return false;

    const rating = ratings[deck.id];
    if (state.quickMode === "morph" && !deck.hasMorph) return false;
    if (state.quickMode === "animated" && !deck.hasAnimation) return false;
    if (state.quickMode === "graded" && (!rating || (!rating.tier && rating.stars === 0 && !rating.notes.trim()))) {
      return false;
    }
    if (state.quickMode === "top-tier" && (!rating || (rating.tier !== "S" && rating.tier !== "A"))) {
      return false;
    }

    if (state.search.trim().length > 0) {
      const q = state.search.trim().toLowerCase();
      const haystack = [
        deck.title,
        deck.description,
        deck.category,
        deck.industry,
        ...deck.tags,
        ...deck.fonts,
        ...deck.colors,
      ]
        .join(" ")
        .toLowerCase();
      if (!haystack.includes(q)) return false;
    }

    return true;
  }

  function getFilteredSortedDecks(): DeckItem[] {
    const matched = decks.filter((d) => deckMatchesFilters(d));
    if (state.sortMode === "slides-desc") {
      matched.sort((a, b) => b.slidesCount - a.slidesCount);
    } else if (state.sortMode === "morph-desc") {
      matched.sort((a, b) => b.morphSlides - a.morphSlides);
    } else if (state.sortMode === "rating-desc") {
      matched.sort((a, b) => (ratings[b.id]?.stars ?? 0) - (ratings[a.id]?.stars ?? 0));
    }
    return matched;
  }

  function renderGrid(appendOnly: boolean = false): void {
    if (!grid) return;
    const matched = getFilteredSortedDecks();
    const visibleCount = matched.length;
    const targetSlice = matched.slice(0, state.pageLimit);
    const sig = targetSlice.map((d) => d.id).join(",");

    if (renderedSignature === "" && sig === Array.from(grid.querySelectorAll<HTMLElement>(".deck-card")).map((c) => c.dataset.deckId).join(",")) {
      renderedSignature = sig;
    } else if (appendOnly && sig.startsWith(renderedSignature + ",")) {
      const existingCount = grid.querySelectorAll(".deck-card").length;
      const frag = document.createDocumentFragment();
      for (let i = existingCount; i < targetSlice.length; i++) {
        frag.appendChild(buildDeckCardElement(targetSlice[i], i));
      }
      grid.appendChild(frag);
      renderedSignature = sig;
    } else if (sig !== renderedSignature) {
      const frag = document.createDocumentFragment();
      targetSlice.forEach((d, i) => frag.appendChild(buildDeckCardElement(d, i)));
      grid.innerHTML = "";
      grid.appendChild(frag);
      renderedSignature = sig;
    }

    const shownCount = targetSlice.length;
    if (loadMoreWrap) {
      const hasMore = visibleCount > shownCount;
      loadMoreWrap.classList.toggle("hidden", !hasMore);
      loadMoreWrap.classList.toggle("flex", hasMore);
      if (loadMoreCaption) {
        loadMoreCaption.textContent = `Showing ${shownCount} of ${visibleCount} matching specimens`;
      }
    }

    if (resultCountEl) {
      resultCountEl.textContent = `${visibleCount} of ${decks.length} decks`;
    }
    if (filterMatchLabel) {
      filterMatchLabel.textContent = `${visibleCount} matching`;
    }
    if (emptyState) {
      emptyState.classList.toggle("hidden", visibleCount > 0);
    }

    const totalFilters = state.categories.size + state.industries.size;
    if (filterBadge) {
      filterBadge.textContent = String(totalFilters);
      filterBadge.classList.toggle("hidden", totalFilters === 0);
    }

    document.querySelectorAll<HTMLButtonElement>("[data-quick-filter]").forEach((btn) => {
      const active = btn.dataset.quickFilter === state.quickMode;
      btn.classList.toggle("brut-btn-primary", active);
      btn.classList.toggle("brut-btn", !active);
    });

    document.querySelectorAll<HTMLButtonElement>("[data-category-pill]").forEach((btn) => {
      const pillVal = btn.dataset.categoryPill ?? "all";
      const active =
        pillVal === "all"
          ? state.categories.size === 0
          : state.categories.size === 1 && state.categories.has(pillVal);
      btn.classList.toggle("brut-btn-primary", active);
      btn.classList.toggle("brut-btn", !active);
    });

    renderActiveChips();
    updateCardGradeBadges();
  }

  // Smooth Infinite Scroll + Load More Button
  loadMoreBtn?.addEventListener("click", () => {
    state.pageLimit += 24;
    renderGrid(true);
  });

  if (sentinelEl && "IntersectionObserver" in window) {
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((en) => en.isIntersecting)) {
          const matched = getFilteredSortedDecks();
          if (state.pageLimit < matched.length) {
            state.pageLimit += 24;
            renderGrid(true);
          }
        }
      },
      { rootMargin: "420px" }
    );
    io.observe(sentinelEl);
  }

  function renderActiveChips(): void {
    if (!activeChipsContainer) return;
    activeChipsContainer.innerHTML = "";
    const chips: Array<{ kind: "category" | "industry"; value: string }> = [
      ...Array.from(state.categories).map((value) => ({ kind: "category" as const, value })),
      ...Array.from(state.industries).map((value) => ({ kind: "industry" as const, value })),
    ];

    if (chips.length === 0) {
      activeChipsContainer.classList.add("hidden");
      return;
    }

    activeChipsContainer.classList.remove("hidden");
    for (const chip of chips) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className =
        "inline-flex items-center gap-1.5 rounded-full border border-[#242832] bg-[#12141A] px-3 py-1 text-xs text-zinc-200 hover:border-[#FF784E] cursor-pointer";
      btn.innerHTML = `<span class="text-zinc-400">${chip.kind === "category" ? "Cat:" : "Ind:"}</span><span>${esc(chip.value)}</span><span class="text-zinc-400">×</span>`;
      btn.addEventListener("click", () => {
        if (chip.kind === "category") state.categories.delete(chip.value);
        else state.industries.delete(chip.value);
        state.pageLimit = 24;
        syncFilterModalButtons();
        renderGrid();
      });
      activeChipsContainer.appendChild(btn);
    }
  }

  function syncFilterModalButtons(): void {
    document.querySelectorAll<HTMLButtonElement>(".filter-option-btn").forEach((btn) => {
      const kind = btn.dataset.filterKind;
      const val = btn.dataset.filterValue ?? "";
      const selected =
        kind === "category" ? state.categories.has(val) : state.industries.has(val);
      btn.classList.toggle("border-white/50", selected);
      btn.classList.toggle("bg-[#202024]", selected);
      const box = btn.querySelector(".filter-check-box");
      if (box) {
        box.classList.toggle("bg-white", selected);
        box.classList.toggle("border-white", selected);
        box.classList.toggle("text-[#0D0D0F]", selected);
        box.classList.toggle("bg-[#18181B]", !selected);
        box.classList.toggle("text-transparent", !selected);
      }
    });

    const catCount = document.getElementById("pane-category-selected-count");
    const indCount = document.getElementById("pane-industry-selected-count");
    if (catCount) {
      catCount.textContent = state.categories.size > 0 ? `${state.categories.size} active` : "10";
    }
    if (indCount) {
      indCount.textContent = state.industries.size > 0 ? `${state.industries.size} active` : "29";
    }
  }

  function openFilterModal(): void {
    if (!filterBackdrop || !filterPanel) return;
    filterBackdrop.classList.remove("hidden");
    filterBackdrop.classList.add("flex");
    filterPanel.setAttribute("data-open", "true");
    document.body.classList.add("modal-open");
    syncFilterModalButtons();
    window.setTimeout(() => filterSearch?.focus(), 40);
  }

  function closeFilterModal(): void {
    if (!filterBackdrop || !filterPanel) return;
    filterPanel.setAttribute("data-open", "false");
    filterBackdrop.classList.add("hidden");
    filterBackdrop.classList.remove("flex");
    document.body.classList.remove("modal-open");
  }

  function renderScoreboard(): void {
    const totalGradedEl = document.getElementById("scoreboard-total-graded");
    const avgStarsEl = document.getElementById("scoreboard-avg-stars");
    const topTierEl = document.getElementById("scoreboard-top-tier");
    const listEl = document.getElementById("scoreboard-category-list");
    if (!listEl) return;

    const allRated = Object.values(ratings).filter((r) => r.stars > 0 || r.tier !== null);
    const starred = allRated.filter((r) => r.stars > 0);
    const avg =
      starred.length > 0
        ? (starred.reduce((acc, r) => acc + r.stars, 0) / starred.length).toFixed(1)
        : "—";
    const topTierCount = allRated.filter((r) => r.tier === "S" || r.tier === "A").length;

    if (totalGradedEl) totalGradedEl.textContent = String(allRated.length);
    if (avgStarsEl) avgStarsEl.textContent = avg === "—" ? "—" : `${avg}★`;
    if (topTierEl) topTierEl.textContent = String(topTierCount);

    listEl.innerHTML = "";
    for (const category of DECK_CATEGORIES) {
      const catDecks = decks.filter((d) => d.category === category);
      const catRatings = catDecks
        .map((d) => ratings[d.id])
        .filter((r): r is BosRatingRecord => Boolean(r && (r.stars > 0 || r.tier)));
      const catStarred = catRatings.filter((r) => r.stars > 0);
      const catAvg =
        catStarred.length > 0
          ? (catStarred.reduce((sum, r) => sum + r.stars, 0) / catStarred.length).toFixed(1)
          : "—";
      const sCount = catRatings.filter((r) => r.tier === "S").length;
      const aCount = catRatings.filter((r) => r.tier === "A").length;

      const row = document.createElement("button");
      row.type = "button";
      row.className =
        "flex w-full items-center justify-between rounded-xl border border-[#242832] bg-[#0A0B0E] px-3.5 py-3 text-left transition-colors hover:border-[#FF784E] cursor-pointer";
      row.innerHTML = `
        <div>
          <div class="flex items-center gap-2">
            <span class="text-xs font-semibold text-white">${category}</span>
            <span class="font-mono text-[10px] text-zinc-400">${catDecks.length} decks</span>
          </div>
          <div class="mt-1 flex items-center gap-2 font-mono text-[10px] text-zinc-400">
            <span>Graded: ${catRatings.length}</span>
            ${sCount > 0 ? `<span class="text-emerald-400">S:${sCount}</span>` : ""}
            ${aCount > 0 ? `<span class="text-violet-400">A:${aCount}</span>` : ""}
          </div>
        </div>
        <div class="text-right">
          <span class="font-mono text-sm font-semibold ${catAvg === "—" ? "text-zinc-600" : "text-amber-400"}">
            ${catAvg === "—" ? "—" : `${catAvg}★`}
          </span>
        </div>
      `;
      row.addEventListener("click", () => {
        state.categories.clear();
        state.categories.add(category);
        state.pageLimit = 24;
        syncFilterModalButtons();
        renderGrid();
        closeScoreboard();
      });
      listEl.appendChild(row);
    }
  }

  function openScoreboard(): void {
    if (!scoreboardBackdrop || !scoreboardPanel) return;
    renderScoreboard();
    scoreboardBackdrop.classList.remove("hidden");
    scoreboardBackdrop.classList.add("flex");
    scoreboardPanel.setAttribute("data-open", "true");
    document.body.classList.add("modal-open");
  }

  function closeScoreboard(): void {
    if (!scoreboardBackdrop || !scoreboardPanel) return;
    scoreboardPanel.setAttribute("data-open", "false");
    scoreboardBackdrop.classList.add("hidden");
    scoreboardBackdrop.classList.remove("flex");
    document.body.classList.remove("modal-open");
  }

  function getActiveDeck(): DeckItem | null {
    if (!state.activeDeckSlug) return null;
    return deckBySlug.get(state.activeDeckSlug) ?? null;
  }

  function updateDeckNavChrome(): void {
    const list = getFilteredSortedDecks();
    const curSlug = state.activeDeckSlug;
    const idx = curSlug ? list.findIndex((d) => d.slug === curSlug) : -1;
    if (viewerDeckPosition) {
      viewerDeckPosition.textContent = idx >= 0 ? `PPT ${idx + 1} / ${list.length}` : `${list.length}`;
    }
    if (viewerPrevDeckBtn) viewerPrevDeckBtn.disabled = list.length <= 1;
    if (viewerNextDeckBtn) viewerNextDeckBtn.disabled = list.length <= 1;
  }

  function navigateDeckByOffset(offset: number): void {
    const list = getFilteredSortedDecks();
    if (list.length === 0) return;
    const curIdx = state.activeDeckSlug ? list.findIndex((d) => d.slug === state.activeDeckSlug) : 0;
    const nextIdx = ((curIdx >= 0 ? curIdx : 0) + offset + list.length) % list.length;
    const nextDeck = list[nextIdx];
    if (!nextDeck) return;
    openDeckViewer(nextDeck.slug, true);
  }

  function navigateNextUnreviewed(): void {
    const list = getFilteredSortedDecks();
    if (list.length === 0) return;
    const curIdx = state.activeDeckSlug ? list.findIndex((d) => d.slug === state.activeDeckSlug) : -1;
    for (let step = 1; step <= list.length; step++) {
      const candidate = list[(curIdx + step + list.length) % list.length];
      const rec = ratings[candidate.id];
      if (!rec || (!rec.tier && rec.stars === 0)) {
        openDeckViewer(candidate.slug, true);
        return;
      }
    }
    showToast("All visible PPTs already reviewed!");
  }

  function stopAutoPlay(): void {
    if (autoPlayTimer !== null) {
      window.clearInterval(autoPlayTimer);
      autoPlayTimer = null;
    }
    if (viewerAutoPlayIcon) viewerAutoPlayIcon.textContent = "▶";
    if (viewerAutoPlayLabel) viewerAutoPlayLabel.textContent = "Auto-Play Effects";
  }

  function toggleAutoPlay(): void {
    if (autoPlayTimer !== null) {
      stopAutoPlay();
      return;
    }
    if (viewerAutoPlayIcon) viewerAutoPlayIcon.textContent = "⏸";
    if (viewerAutoPlayLabel) viewerAutoPlayLabel.textContent = "Playing Live...";
    const deck = getActiveDeck();
    if (deck) {
      const slides = deck.slidesPreview.length > 0 ? deck.slidesPreview : [deck.coverImage];
      renderSlideAt((state.activeSlideIndex + 1) % slides.length, true);
    }
    autoPlayTimer = window.setInterval(() => {
      const curDeck = getActiveDeck();
      if (!curDeck) {
        stopAutoPlay();
        return;
      }
      const slides = curDeck.slidesPreview.length > 0 ? curDeck.slidesPreview : [curDeck.coverImage];
      renderSlideAt((state.activeSlideIndex + 1) % slides.length, true);
    }, 2000);
  }

  function syncFxButtons(): void {
    document.querySelectorAll<HTMLButtonElement>("[data-fx-mode]").forEach((btn) => {
      const active = btn.dataset.fxMode === state.fxMode;
      btn.classList.toggle("bg-white", active);
      btn.classList.toggle("text-[#0D0D0F]", active);
      btn.classList.toggle("border-white", active);
      btn.classList.toggle("font-semibold", active);
      btn.classList.toggle("bg-[#18181B]", !active);
      btn.classList.toggle("text-zinc-300", !active);
      btn.classList.toggle("border-[#27272A]", !active);
    });
  }

  function animateStageLiveActors(deck: DeckItem, slideIndex: number, totalSlides: number): void {
    const ratio = (slideIndex + 1) / Math.max(1, totalSlides);
    const accent = deck.colors[0] && !/^#(0D0D0F|18181B|FFFFFF|FAFAFA|111317)$/i.test(deck.colors[0])
      ? deck.colors[0]
      : deck.colors[1] || "#E8491D";

    if (fxLiveProgress) {
      fxLiveProgress.style.width = `${Math.round(ratio * 100)}%`;
      fxLiveProgress.style.backgroundColor = accent;
    }
    if (fxLiveRule) {
      fxLiveRule.style.width = `${Math.round(25 + ratio * 65)}%`;
      fxLiveRule.style.backgroundColor = accent;
    }
    if (fxLivePrism) {
      const deg = (slideIndex * 45) % 360;
      const topPct = 14 + Math.round((slideIndex / Math.max(1, totalSlides - 1)) * 52);
      fxLivePrism.style.top = `${topPct}%`;
      fxLivePrism.style.transform = `rotate(${deg}deg) scale(${slideIndex % 2 === 0 ? 1 : 1.2})`;
      fxLivePrism.style.borderColor = accent;
    }
    if (fxLiveNum) {
      fxLiveNum.textContent = String(slideIndex + 1).padStart(2, "0");
      fxLiveNum.style.transform = `translate3d(${slideIndex % 2 === 0 ? "0px" : "-22px"}, ${slideIndex % 2 === 0 ? "0px" : "-12px"}, 0)`;
    }
  }

  function renderSlideAt(index: number, animate: boolean = true): void {
    const deck = getActiveDeck();
    if (!deck || !viewerActiveImg || !viewerSlideCounter || !viewerThumbStrip) return;
    const slides = deck.slidesPreview.length > 0 ? deck.slidesPreview : [deck.coverImage];
    const clamped = Math.max(0, Math.min(index, slides.length - 1));
    const prevSrc = viewerActiveImg.getAttribute("src") || "";
    state.activeSlideIndex = clamped;

    const fxClasses = [
      "fx-morph-enter", "fx-morph-leave",
      "fx-kinetic-enter", "fx-kinetic-leave",
      "fx-wipe-enter", "fx-wipe-leave",
    ];
    viewerActiveImg.classList.remove(...fxClasses);
    viewerPrevBufferImg?.classList.remove(...fxClasses);

    if (animate && prevSrc && viewerPrevBufferImg) {
      viewerPrevBufferImg.src = prevSrc;
      viewerPrevBufferImg.style.opacity = "1";
    } else if (viewerPrevBufferImg) {
      viewerPrevBufferImg.style.opacity = "0";
    }

    viewerActiveImg.src = slides[clamped];
    viewerActiveImg.alt = `${deck.title} — Slide ${clamped + 1}`;
    viewerSlideCounter.textContent = `${clamped + 1} / ${slides.length}`;

    if (animate) {
      void viewerActiveImg.offsetWidth;
      const enterCls =
        state.fxMode === "kinetic"
          ? "fx-kinetic-enter"
          : state.fxMode === "wipe"
            ? "fx-wipe-enter"
            : "fx-morph-enter";
      const leaveCls =
        state.fxMode === "kinetic"
          ? "fx-kinetic-leave"
          : state.fxMode === "wipe"
            ? "fx-wipe-leave"
            : "fx-morph-leave";
      viewerActiveImg.classList.add(enterCls);
      if (viewerPrevBufferImg && prevSrc) {
        viewerPrevBufferImg.classList.add(leaveCls);
      }
    }

    animateStageLiveActors(deck, clamped, slides.length);

    if (viewerPrevBtn) viewerPrevBtn.disabled = slides.length <= 1;
    if (viewerNextBtn) viewerNextBtn.disabled = slides.length <= 1;

    viewerThumbStrip.querySelectorAll<HTMLButtonElement>("[data-slide-idx]").forEach((thumb) => {
      const isCurrent = Number(thumb.dataset.slideIdx) === clamped;
      thumb.classList.toggle("border-white", isCurrent);
      thumb.classList.toggle("opacity-100", isCurrent);
      thumb.classList.toggle("border-[#27272A]", !isCurrent);
      thumb.classList.toggle("opacity-55", !isCurrent);
      if (isCurrent) {
        thumb.scrollIntoView({ behavior: "smooth", inline: "nearest", block: "nearest" });
      }
    });
  }

  function renderViewerGrading(deck: DeckItem): void {
    const rec: BosRatingRecord = ratings[deck.id] ?? {
      deckId: deck.id,
      slug: deck.slug,
      title: deck.title,
      category: deck.category,
      tier: null,
      stars: 0,
      notes: "",
      updatedAt: new Date().toISOString(),
    };

    document.querySelectorAll<HTMLButtonElement>(".bos-tier-btn").forEach((btn) => {
      const active = btn.dataset.bosTier === rec.tier;
      btn.classList.toggle("bg-white", active);
      btn.classList.toggle("text-[#0D0D0F]", active);
      btn.classList.toggle("border-white", active);
      btn.classList.toggle("bg-[#0D0D0F]", !active);
      btn.classList.toggle("text-zinc-400", !active);
    });

    document.querySelectorAll<HTMLButtonElement>(".bos-star-btn").forEach((btn) => {
      const starVal = Number(btn.dataset.bosStar ?? 0);
      const lit = starVal <= rec.stars;
      btn.classList.toggle("text-amber-400", lit);
      btn.classList.toggle("text-zinc-600", !lit);
    });

    if (bosNotesInput && bosNotesInput.value !== rec.notes) {
      bosNotesInput.value = rec.notes;
    }
  }

  function updateDeckRating(patch: Partial<BosRatingRecord>): void {
    const deck = getActiveDeck();
    if (!deck) return;
    const prev: BosRatingRecord = ratings[deck.id] ?? {
      deckId: deck.id,
      slug: deck.slug,
      title: deck.title,
      category: deck.category,
      tier: null,
      stars: 0,
      notes: "",
      updatedAt: new Date().toISOString(),
    };
    const next: BosRatingRecord = {
      ...prev,
      ...patch,
      updatedAt: new Date().toISOString(),
    };
    ratings = { ...ratings, [deck.id]: next };
    saveRatings(ratings);
    renderViewerGrading(deck);
    updateCardGradeBadges();

    if (bosSavedStatus) {
      bosSavedStatus.classList.remove("opacity-0");
      window.setTimeout(() => bosSavedStatus.classList.add("opacity-0"), 1400);
    }
  }

  function openDeckViewer(slug: string, deckSwitched: boolean = false): void {
    const deck = deckBySlug.get(slug);
    if (!deck || !viewerBackdrop || !viewerPanel) return;

    state.activeDeckSlug = slug;
    state.activeSlideIndex = 0;

    if (viewerStageFrame && deckSwitched) {
      viewerStageFrame.classList.remove("fx-deck-switch");
      void viewerStageFrame.offsetWidth;
      viewerStageFrame.classList.add("fx-deck-switch");
    }

    const url = new URL(window.location.href);
    url.searchParams.set("deck", slug);
    window.history.replaceState({}, "", url.toString());

    updateDeckNavChrome();

    if (viewerTitle) viewerTitle.textContent = deck.title;
    if (viewerPermalink) viewerPermalink.href = `/deck/${deck.slug}`;
    if (viewerDownloadBtn) viewerDownloadBtn.href = deck.pptxUrl;
    if (viewerDescription) viewerDescription.textContent = deck.description;
    if (viewerBlueprintSummary) viewerBlueprintSummary.textContent = deck.blueprintSummary;

    if (viewerMetaPills) {
      viewerMetaPills.innerHTML = `
        <span class="rounded-full border border-[#27272A] bg-[#18181B] px-2.5 py-0.5 text-[11px] text-zinc-300">${esc(deck.category)}</span>
        <span class="rounded-full border border-[#27272A] bg-[#18181B] px-2.5 py-0.5 text-[11px] text-zinc-400">${esc(deck.industry)}</span>
        ${deck.hasMorph ? `<span class="rounded-full border border-violet-400/35 bg-violet-500/10 px-2.5 py-0.5 font-mono text-[10px] text-violet-300">✦ Morph</span>` : ""}
        ${deck.hasAnimation ? `<span class="rounded-full border border-amber-400/35 bg-amber-500/10 px-2.5 py-0.5 font-mono text-[10px] text-amber-300">⚡ Anim</span>` : ""}
      `;
    }

    if (viewerTags) {
      viewerTags.innerHTML = deck.tags
        .map(
          (t) =>
            `<span class="rounded-full border border-[#27272A] bg-[#0D0D0F] px-2.5 py-0.5 text-[10px] text-zinc-400">${esc(t)}</span>`
        )
        .join("");
    }

    if (viewerSwatches) {
      viewerSwatches.innerHTML = "";
      for (const hex of deck.colors) {
        const swatchBtn = document.createElement("button");
        swatchBtn.type = "button";
        swatchBtn.className =
          "inline-flex items-center gap-2 rounded-full border border-[#27272A] bg-[#0D0D0F] px-2.5 py-1 font-mono text-[11px] text-zinc-200 transition-colors hover:border-zinc-500 cursor-pointer";
        swatchBtn.innerHTML = `<span class="h-3.5 w-3.5 rounded-full border border-white/20" style="background-color:${esc(hex)};"></span><span>${esc(hex)}</span>`;
        swatchBtn.addEventListener("click", () => copyToClipboard(hex, `Copied ${hex}`));
        viewerSwatches.appendChild(swatchBtn);
      }
    }

    if (viewerFonts) {
      viewerFonts.innerHTML = deck.fonts
        .map(
          (f) =>
            `<span class="rounded-lg border border-[#27272A] bg-[#0D0D0F] px-2.5 py-1 font-mono text-[11px] text-zinc-200">${esc(f)}</span>`
        )
        .join("");
    }

    if (viewerOoxmlGrid) {
      const telemetry: Array<[string, string | number]> = [
        ["Slides", deck.slidesCount],
        ["Avg Shapes / Slide", deck.avgShapesPerSlide],
        ["Morph Slides", deck.morphSlides],
        ["Paired !!Morphs", deck.pairedMorphSlides],
        ["Animated Slides", deck.animationSlides],
        ["Source", deck.source],
      ];
      viewerOoxmlGrid.innerHTML = telemetry
        .map(
          ([label, val]) => `
            <div class="rounded-xl border border-[#27272A] bg-[#0D0D0F] px-3 py-2">
              <span class="block text-[10px] text-zinc-500">${esc(label)}</span>
              <span class="mt-0.5 block font-mono text-xs font-semibold text-zinc-100">${esc(val)}</span>
            </div>
          `
        )
        .join("");
    }

    const slides = deck.slidesPreview.length > 0 ? deck.slidesPreview : [deck.coverImage];
    if (viewerThumbStrip) {
      viewerThumbStrip.innerHTML = "";
      slides.forEach((src, idx) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.dataset.slideIdx = String(idx);
        btn.className =
          "relative aspect-video h-14 shrink-0 overflow-hidden rounded-lg border border-[#27272A] bg-[#18181B] transition-all hover:opacity-100 cursor-pointer";
        btn.innerHTML = `<img src="${esc(src)}" alt="Slide ${idx + 1}" class="h-full w-full object-cover" /><span class="absolute bottom-1 right-1 rounded bg-black/75 px-1 font-mono text-[9px] text-zinc-200">${idx + 1}</span>`;
        btn.addEventListener("click", () => renderSlideAt(idx));
        viewerThumbStrip.appendChild(btn);
      });
    }

    renderSlideAt(0, deckSwitched);
    renderViewerGrading(deck);

    viewerBackdrop.classList.remove("hidden");
    viewerPanel.setAttribute("data-open", "true");
    document.body.classList.add("modal-open");
  }

  function closeDeckViewer(): void {
    if (!viewerBackdrop || !viewerPanel) return;
    stopAutoPlay();
    state.activeDeckSlug = null;
    viewerPanel.setAttribute("data-open", "false");
    viewerBackdrop.classList.add("hidden");
    document.body.classList.remove("modal-open");

    const url = new URL(window.location.href);
    url.searchParams.delete("deck");
    window.history.replaceState({}, "", url.toString());
  }

  // Event Wiring: Search & Sort
  let searchDebounce = 0;
  searchInput?.addEventListener("input", () => {
    window.clearTimeout(searchDebounce);
    searchDebounce = window.setTimeout(() => {
      state.search = searchInput.value;
      state.pageLimit = 24;
      renderGrid();
    }, 90);
  });

  sortSelect?.addEventListener("change", () => {
    state.sortMode = sortSelect.value as SortMode;
    state.pageLimit = 24;
    renderGrid();
  });

  document.querySelectorAll<HTMLButtonElement>("[data-quick-filter]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.quickMode = (btn.dataset.quickFilter as QuickMode) || "all";
      state.pageLimit = 24;
      renderGrid();
    });
  });

  document.querySelectorAll<HTMLButtonElement>("[data-category-pill]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const val = btn.dataset.categoryPill ?? "all";
      state.categories.clear();
      if (val !== "all") state.categories.add(val);
      state.pageLimit = 24;
      syncFilterModalButtons();
      renderGrid();
    });
  });

  document.getElementById("reset-all-empty-btn")?.addEventListener("click", () => {
    state.search = "";
    if (searchInput) searchInput.value = "";
    state.categories.clear();
    state.industries.clear();
    state.quickMode = "all";
    state.pageLimit = 24;
    syncFilterModalButtons();
    renderGrid();
  });

  document.getElementById("open-filter-modal-btn")?.addEventListener("click", openFilterModal);
  document.getElementById("close-filter-modal-x")?.addEventListener("click", closeFilterModal);
  document.getElementById("filter-modal-done-btn")?.addEventListener("click", closeFilterModal);
  filterBackdrop?.addEventListener("click", (e) => {
    if (e.target === filterBackdrop) closeFilterModal();
  });

  document.getElementById("filter-modal-clear-btn")?.addEventListener("click", () => {
    state.categories.clear();
    state.industries.clear();
    state.pageLimit = 24;
    if (filterSearch) filterSearch.value = "";
    document.querySelectorAll<HTMLElement>(".filter-option-btn").forEach((el) => el.classList.remove("hidden"));
    syncFilterModalButtons();
    renderGrid();
  });

  document.querySelectorAll<HTMLButtonElement>(".filter-pane-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.filterPaneTab as "category" | "industry";
      state.activePane = target;
      document.querySelectorAll<HTMLButtonElement>(".filter-pane-tab").forEach((t) => {
        const isCurrent = t.dataset.filterPaneTab === target;
        t.classList.toggle("bg-[#27272A]", isCurrent);
        t.classList.toggle("text-white", isCurrent);
        t.classList.toggle("text-zinc-400", !isCurrent);
      });
      const catPane = document.getElementById("filter-pane-category");
      const indPane = document.getElementById("filter-pane-industry");
      catPane?.classList.toggle("hidden", target !== "category");
      catPane?.classList.toggle("grid", target === "category");
      indPane?.classList.toggle("hidden", target !== "industry");
      indPane?.classList.toggle("grid", target === "industry");
    });
  });

  document.querySelectorAll<HTMLButtonElement>(".filter-option-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const kind = btn.dataset.filterKind;
      const value = btn.dataset.filterValue ?? "";
      const targetSet = kind === "category" ? state.categories : state.industries;
      if (targetSet.has(value)) targetSet.delete(value);
      else targetSet.add(value);
      state.pageLimit = 24;
      syncFilterModalButtons();
      renderGrid();
    });
  });

  filterSearch?.addEventListener("input", () => {
    const q = filterSearch.value.trim().toLowerCase();
    document.querySelectorAll<HTMLElement>(".filter-option-btn").forEach((btn) => {
      const val = (btn.dataset.filterValue ?? "").toLowerCase();
      btn.classList.toggle("hidden", q.length > 0 && !val.includes(q));
    });
  });

  document.getElementById("open-scoreboard-btn")?.addEventListener("click", openScoreboard);
  document.getElementById("quickbar-scoreboard-btn")?.addEventListener("click", openScoreboard);
  document.getElementById("close-scoreboard-btn")?.addEventListener("click", closeScoreboard);
  scoreboardBackdrop?.addEventListener("click", (e) => {
    if (e.target === scoreboardBackdrop) closeScoreboard();
  });

  document.getElementById("navbar-export-ratings-btn")?.addEventListener("click", () => exportRatingsJson(decks));
  document.getElementById("scoreboard-export-btn")?.addEventListener("click", () => exportRatingsJson(decks));
  document.getElementById("scoreboard-clear-ratings-btn")?.addEventListener("click", () => {
    ratings = {};
    saveRatings(ratings);
    updateCardGradeBadges();
    renderScoreboard();
    renderGrid();
    showToast("Cleared local Bos ratings");
  });

  // Card Open + Hero Stage Pin + Direct AI Prompt Copy Triggers
  grid?.addEventListener("click", (e) => {
    const target = e.target as HTMLElement;
    if (target.closest("[data-download-pptx]")) return;
    const copyTrigger = target.closest<HTMLElement>("[data-copy-prompt]");
    if (copyTrigger?.dataset.copyPrompt) {
      const deck = deckBySlug.get(copyTrigger.dataset.copyPrompt);
      if (deck) copyToClipboard(buildAiPromptFromDeck(deck), `Copied AI Prompt: ${deck.title}`);
      return;
    }
    const pinTrigger = target.closest<HTMLElement>("[data-pin-hero]");
    if (pinTrigger?.dataset.pinHero) {
      pinHeroDeck(pinTrigger.dataset.pinHero);
      window.scrollTo({ top: 0, behavior: "smooth" });
      showToast("Loaded onto Featured Stage");
      return;
    }
    const trigger = target.closest<HTMLElement>("[data-open-deck]");
    if (trigger?.dataset.openDeck) {
      openDeckViewer(trigger.dataset.openDeck);
    }
  });

  // Live Hover Slide Scrubbing + Slide Counter HUD on Cards
  grid?.addEventListener("mouseover", (e) => {
    const card = (e.target as HTMLElement).closest<HTMLElement>(".deck-card");
    if (!card || (card as HTMLElement & { _scrubTimer?: number })._scrubTimer) return;
    const rawSlides = card.dataset.slidesPreview;
    if (!rawSlides) return;
    let slides: string[] = [];
    try {
      slides = JSON.parse(rawSlides);
    } catch {
      return;
    }
    if (slides.length <= 1) return;
    const imgEl = card.querySelector<HTMLImageElement>(".card-preview-img");
    const progEl = card.querySelector<HTMLElement>(".card-hover-progress");
    const hudEl = card.querySelector<HTMLElement>(".card-slide-hud");
    const origHud = hudEl?.textContent || "";
    if (!imgEl) return;
    let step = 0;
    const tick = () => {
      step = (step + 1) % slides.length;
      imgEl.src = slides[step];
      if (progEl) {
        progEl.style.width = `${Math.round(((step + 1) / slides.length) * 100)}%`;
      }
      if (hudEl) {
        hudEl.textContent = `SL ${String(step + 1).padStart(2, "0")} / ${slides.length}`;
      }
    };
    const tId = window.setInterval(tick, 900);
    (card as HTMLElement & { _scrubTimer?: number })._scrubTimer = tId;
    card.addEventListener(
      "mouseleave",
      () => {
        window.clearInterval(tId);
        delete (card as HTMLElement & { _scrubTimer?: number })._scrubTimer;
        imgEl.src = slides[0];
        if (progEl) progEl.style.width = "16%";
        if (hudEl && origHud) hudEl.textContent = origHud;
      },
      { once: true }
    );
  });

  // Viewer Controls & Motion Stage Events
  document.getElementById("close-deck-viewer-btn")?.addEventListener("click", closeDeckViewer);
  viewerPrevBtn?.addEventListener("click", () => {
    const deck = getActiveDeck();
    if (!deck) return;
    const len = Math.max(1, deck.slidesPreview.length);
    renderSlideAt((state.activeSlideIndex - 1 + len) % len, true);
  });
  viewerNextBtn?.addEventListener("click", () => {
    const deck = getActiveDeck();
    if (!deck) return;
    const len = Math.max(1, deck.slidesPreview.length);
    renderSlideAt((state.activeSlideIndex + 1) % len, true);
  });
  viewerPrevDeckBtn?.addEventListener("click", () => navigateDeckByOffset(-1));
  viewerNextDeckBtn?.addEventListener("click", () => navigateDeckByOffset(1));
  bosNextUnreviewedBtn?.addEventListener("click", navigateNextUnreviewed);
  viewerAutoPlayBtn?.addEventListener("click", toggleAutoPlay);
  viewerReplayFxBtn?.addEventListener("click", () => renderSlideAt(state.activeSlideIndex, true));

  viewerArrowModeBtn?.addEventListener("click", () => {
    state.arrowMode = state.arrowMode === "slide" ? "deck" : "slide";
    if (viewerArrowModeLabel) {
      viewerArrowModeLabel.textContent = state.arrowMode === "deck" ? "PPT Deck" : "Slide";
    }
    showToast(
      state.arrowMode === "deck"
        ? "← / → now switches PPT Decks directly!"
        : "← / → controls Slides (use [ / ] to switch PPT)"
    );
  });

  document.querySelectorAll<HTMLButtonElement>("[data-fx-mode]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.fxMode = (btn.dataset.fxMode as FxMode) || "morph";
      syncFxButtons();
      if (viewerStageFrame && state.fxMode !== "spatial") {
        viewerStageFrame.style.setProperty("--rx", "0deg");
        viewerStageFrame.style.setProperty("--ry", "0deg");
      }
      renderSlideAt(state.activeSlideIndex, true);
    });
  });

  viewerStageFrame?.addEventListener("mousemove", (e) => {
    if (state.fxMode !== "spatial" && state.fxMode !== "kinetic") return;
    const rect = viewerStageFrame.getBoundingClientRect();
    const nx = (e.clientX - rect.left) / rect.width - 0.5;
    const ny = (e.clientY - rect.top) / rect.height - 0.5;
    viewerStageFrame.style.setProperty("--rx", `${(-ny * 10).toFixed(2)}deg`);
    viewerStageFrame.style.setProperty("--ry", `${(nx * 12).toFixed(2)}deg`);
  });

  viewerStageFrame?.addEventListener("mouseleave", () => {
    viewerStageFrame.style.setProperty("--rx", "0deg");
    viewerStageFrame.style.setProperty("--ry", "0deg");
  });

  document.querySelectorAll<HTMLButtonElement>(".bos-tier-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tier = btn.dataset.bosTier as BosTier;
      const deck = getActiveDeck();
      if (!deck) return;
      const currentTier = ratings[deck.id]?.tier ?? null;
      const newTier = currentTier === tier ? null : tier;
      updateDeckRating({ tier: newTier });
      if (newTier && bosAutoNextToggle?.checked) {
        window.setTimeout(() => navigateDeckByOffset(1), 240);
      }
    });
  });

  document.querySelectorAll<HTMLButtonElement>(".bos-star-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const stars = Number(btn.dataset.bosStar ?? 0);
      updateDeckRating({ stars });
    });
  });

  bosNotesInput?.addEventListener("input", () => {
    updateDeckRating({ notes: bosNotesInput.value });
  });

  document.getElementById("viewer-copy-json-btn")?.addEventListener("click", () => {
    const deck = getActiveDeck();
    if (!deck) return;
    copyToClipboard(JSON.stringify(deck, null, 2), "Copied AI Blueprint JSON");
  });

  document.getElementById("viewer-copy-prompt-btn")?.addEventListener("click", () => {
    const deck = getActiveDeck();
    if (!deck) return;
    copyToClipboard(buildAiPromptFromDeck(deck), "Copied AI Design Prompt");
  });

  window.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      searchInput?.focus();
      searchInput?.select();
      return;
    }

    const viewerOpen = state.activeDeckSlug !== null;
    if (viewerOpen) {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "TEXTAREA" || tag === "INPUT") {
        if (e.key === "Escape") closeDeckViewer();
        return;
      }
      if (e.key === "Escape") {
        closeDeckViewer();
      } else if (e.key === "[" || (e.shiftKey && e.key === "ArrowLeft")) {
        e.preventDefault();
        navigateDeckByOffset(-1);
      } else if (e.key === "]" || (e.shiftKey && e.key === "ArrowRight")) {
        e.preventDefault();
        navigateDeckByOffset(1);
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        if (state.arrowMode === "deck") navigateDeckByOffset(-1);
        else {
          const len = Math.max(1, getActiveDeck()?.slidesPreview.length ?? 1);
          renderSlideAt((state.activeSlideIndex - 1 + len) % len, true);
        }
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        if (state.arrowMode === "deck") navigateDeckByOffset(1);
        else {
          const len = Math.max(1, getActiveDeck()?.slidesPreview.length ?? 1);
          renderSlideAt((state.activeSlideIndex + 1) % len, true);
        }
      } else if (e.key === " ") {
        e.preventDefault();
        toggleAutoPlay();
      } else if (["s", "a", "b", "c"].includes(e.key.toLowerCase())) {
        const tier = e.key.toUpperCase() as BosTier;
        updateDeckRating({ tier });
        if (bosAutoNextToggle?.checked) {
          window.setTimeout(() => navigateDeckByOffset(1), 240);
        }
      } else if (["1", "2", "3", "4", "5"].includes(e.key)) {
        updateDeckRating({ stars: Number(e.key) });
      }
      return;
    }

    if (e.key === "Escape") {
      closeFilterModal();
      closeScoreboard();
    }
  });

  syncFilterModalButtons();
  renderGrid();

  const initialSlug = new URLSearchParams(window.location.search).get("deck");
  if (initialSlug && deckBySlug.has(initialSlug)) {
    openDeckViewer(initialSlug);
  }
}
