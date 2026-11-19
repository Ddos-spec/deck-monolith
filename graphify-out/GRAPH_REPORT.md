# Graph Report - deck_gallery  (2026-11-19)

## Corpus Check
- 16 files · ~143,584 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 2 file(s) not represented in the graph (top: (none) 1, .css 1)

## Summary
- 100 nodes · 177 edges · 12 communities
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 7 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11

## God Nodes (most connected - your core abstractions)
1. `initDeckGallery()` - 32 edges
2. `openDeckViewer()` - 7 edges
3. `DeckItem` - 6 edges
4. `renderGrid()` - 6 edges
5. `scripts` - 5 edges
6. `saveRatings()` - 5 edges
7. `showToast()` - 5 edges
8. `copyToClipboard()` - 5 edges
9. `renderScoreboard()` - 5 edges
10. `getFilteredSortedDecks()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `initDeckGallery()` --calls--> `buildAiPromptFromDeck()`  [EXTRACTED]
  src/scripts/gallery.ts → src/lib/deckCatalog.ts
- `patchRating()` --calls--> `saveRatings()`  [EXTRACTED]
  src/pages/deck/[slug].astro → src/scripts/gallery.ts

## Import Cycles
- None detected.

## Communities (12 total, 0 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.17
Nodes (14): dependencies, astro@^5.18.2, tailwindcss@^4.3.5, @tailwindcss/vite@^4.3.5, devDependencies, typescript@^5.8.3, name, private (+6 more)

### Community 1 - "Community 1"
Cohesion: 0.14
Nodes (8): Props, Props, buildCategoryCounts(), buildIndustryCounts(), categoryCounts, dataEl, decks, industryCounts

### Community 2 - "Community 2"
Cohesion: 0.35
Nodes (9): initDeckGallery(), closeScoreboard(), deckMatchesFilters(), openFilterModal(), openScoreboard(), renderActiveChips(), renderGrid(), renderScoreboard() (+1 more)

### Community 3 - "Community 3"
Cohesion: 0.28
Nodes (6): BosRatingRecord, buildAiPromptFromDeck(), patchRating(), Props, renderGrading(), saveRatings()

### Community 4 - "Community 4"
Cohesion: 0.31
Nodes (9): copyToClipboard(), exportRatingsJson(), getFilteredSortedDecks(), navigateDeckByOffset(), navigateNextUnreviewed(), openDeckViewer(), updateDeckNavChrome(), loadRatings() (+1 more)

### Community 5 - "Community 5"
Cohesion: 0.25
Nodes (7): BOS_RATINGS_STORAGE_KEY, BosTier, ArrowMode, FxMode, GalleryState, QuickMode, SortMode

### Community 6 - "Community 6"
Cohesion: 0.33
Nodes (3): Props, DECK_CATEGORIES, DECK_INDUSTRIES

### Community 7 - "Community 7"
Cohesion: 0.40
Nodes (4): Props, DeckCategory, DeckIndustry, DeckItem

### Community 8 - "Community 8"
Cohesion: 0.40
Nodes (6): animateStageLiveActors(), closeDeckViewer(), getActiveDeck(), renderSlideAt(), stopAutoPlay(), toggleAutoPlay()

### Community 9 - "Community 9"
Cohesion: 0.40
Nodes (5): scripts, astro, build, dev, preview

### Community 10 - "Community 10"
Cohesion: 0.40
Nodes (4): astro/tsconfigs/strict, exclude, extends, include

### Community 11 - "Community 11"
Cohesion: 0.50
Nodes (4): renderViewerGrading(), updateCardGradeBadges(), updateDeckRating(), tierBadgeClass()

## Knowledge Gaps
- **28 isolated node(s):** `name`, `type`, `version`, `private`, `dev` (+23 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 36 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `initDeckGallery()` connect `Community 2` to `Community 8`, `Community 11`, `Community 3`, `Community 4`?**
  _High betweenness centrality (0.008) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `initDeckGallery()` (e.g. with `closeDeckViewer()` and `closeFilterModal()`) actually correct?**
  _`initDeckGallery()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `type`, `version` to the rest of the system?**
  _28 weakly-connected nodes found - possible missing edges._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._
- **Why does `openDeckViewer()` connect `Community 4` to `Community 8`, `Community 11`?**
  _High betweenness centrality (0.001) - this node is a cross-community bridge._
- **Why does `renderGrid()` connect `Community 2` to `Community 11`?**
  _High betweenness centrality (0.001) - this node is a cross-community bridge._