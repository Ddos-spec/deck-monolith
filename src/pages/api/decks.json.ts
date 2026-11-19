import type { APIRoute } from "astro";
import decksData from "../../data/decks.json";
import { DECK_CATEGORIES, DECK_INDUSTRIES, type DeckItem } from "../../lib/deckCatalog";

export const GET: APIRoute = () => {
  const decks = decksData as DeckItem[];
  const payload = {
    name: "DECK.MONOLITH — Brutalist Presentation Archive",
    version: "2.0.0",
    generatedAt: new Date().toISOString(),
    totalDecks: decks.length,
    categories: DECK_CATEGORIES,
    industries: DECK_INDUSTRIES,
    decks,
  };

  return new Response(JSON.stringify(payload, null, 2), {
    status: 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  });
};
