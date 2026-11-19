export const DECK_CATEGORIES = [
  "Pitch",
  "Guideline",
  "Report",
  "Talks",
  "Portfolio",
  "Marketing",
  "Sales",
  "Strategy",
  "Proposal",
  "Other",
] as const;

export const DECK_INDUSTRIES = [
  "Agency",
  "Media",
  "SaaS",
  "Consumer",
  "Fashion",
  "Fintech",
  "Crypto",
  "Enterprise",
  "Travel",
  "Mobility",
  "Climate",
  "Ecommerce",
  "Food & Beverage",
  "Sports",
  "Real Estate",
  "Marketplace",
  "Gaming",
  "Hardware",
  "Healthcare",
  "Aerospace",
  "AI",
  "Industrial",
  "Beauty",
  "Education",
  "HR",
  "Logistics",
  "Non-Profit",
  "Security",
  "Other",
] as const;

export type DeckCategory = (typeof DECK_CATEGORIES)[number];
export type DeckIndustry = (typeof DECK_INDUSTRIES)[number];

export interface DeckItem {
  id: string;
  slug: string;
  title: string;
  description: string;
  category: string;
  industry: string;
  designFamily?: string;
  tags: string[];
  slidesCount: number;
  avgShapesPerSlide: number;
  morphSlides: number;
  pairedMorphSlides: number;
  animationSlides: number;
  hasMorph: boolean;
  hasAnimation: boolean;
  fonts: string[];
  colors: string[];
  source: string;
  sourceUrl: string;
  pptxUrl: string;
  coverImage: string;
  slidesPreview: string[];
  blueprintSummary: string;
}

export type BosTier = "S" | "A" | "B" | "C";

export interface BosRatingRecord {
  deckId: string;
  slug: string;
  title: string;
  category: string;
  tier: BosTier | null;
  stars: number; // 0..5
  notes: string;
  updatedAt: string;
}

export const BOS_RATINGS_STORAGE_KEY = "deck_vault_bos_ratings_v1";

export function buildCategoryCounts(decks: DeckItem[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const cat of DECK_CATEGORIES) counts[cat] = 0;
  for (const deck of decks) {
    const key = DECK_CATEGORIES.includes(deck.category as DeckCategory) ? deck.category : "Other";
    counts[key] = (counts[key] ?? 0) + 1;
  }
  return counts;
}

export function buildIndustryCounts(decks: DeckItem[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const ind of DECK_INDUSTRIES) counts[ind] = 0;
  for (const deck of decks) {
    const key = DECK_INDUSTRIES.includes(deck.industry as DeckIndustry) ? deck.industry : "Other";
    counts[key] = (counts[key] ?? 0) + 1;
  }
  return counts;
}

export function buildAiPromptFromDeck(deck: DeckItem): string {
  const palette = deck.colors.length ? deck.colors.join(", ") : "#F2EFE9, #111111, #C22F10";
  const fonts = deck.fonts.length ? deck.fonts.join(" + ") : "Grotesk Headline + Editorial Serif";
  const morphRatio = deck.slidesCount > 0 ? Math.round((deck.morphSlides / deck.slidesCount) * 100) : 0;
  const familyLine = deck.designFamily ? `Design System: ${deck.designFamily}` : "Design System: Editorial Archive";

  return [
    `Create a ${deck.slidesCount}-slide 16:9 presentation inspired by "${deck.title}" (${deck.category} · ${deck.industry}).`,
    familyLine,
    ``,
    `Design Tokens:`,
    `- Color Palette: ${palette}`,
    `- Typography Pairing: ${fonts}`,
    `- Composition Target: ~${deck.avgShapesPerSlide} elements/slide`,
    `- Motion Spec: ${deck.hasMorph ? `PowerPoint Morph on ${deck.morphSlides}/${deck.slidesCount} slides (${morphRatio}%), ${deck.pairedMorphSlides} tracked !!actors` : "Clean architectural cuts"}; ${deck.hasAnimation ? `${deck.animationSlides} animated slides` : "Minimal entrance motion"}`,
    ``,
    `Architectural Blueprint:`,
    `${deck.blueprintSummary}`,
    ``,
    `Generation Rules:`,
    `- Preserve generous margins, stark typographic contrast, and consistent 16:9 hierarchy.`,
    `- Pair !!prefixed shape names across adjacent slides whenever animating focal elements via Morph.`,
  ].join("\n");
}
