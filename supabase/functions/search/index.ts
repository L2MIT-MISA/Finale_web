import { normalizeText } from "./normalize/normalizeText.ts";
import { correctTypos } from "./correction/correctTypos.ts";
import { parseQuery, determineType } from "./parser/parseQuery.ts";
import { geocode } from "./geocoding/geocode.ts";
import type { SearchResult } from "./types/search.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type"
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", {
      headers: corsHeaders
    });
  }

  try {
    const body = await req.json();
    const query = body.query;

    if (typeof query !== "string" || query.trim() === "") {
      return new Response(
        JSON.stringify({
          error: "Le champ query est obligatoire."
        }),
        {
          status: 400,
          headers: {
            ...corsHeaders,
            "Content-Type": "application/json"
          }
        }
      );
    }

    const normalizedQuery = normalizeText(query);
    const correctedQuery = correctTypos(normalizedQuery);

    const parsed = parseQuery(correctedQuery);

    // Le parseur propose un candidat de lieu ; l'API dit si c'est un vrai lieu.
    let location: string | null = parsed.location;
    let locationVerified: boolean | null = null;
    let place: SearchResult["place"] = null;

    if (parsed.location) {
      const found = await geocode(parsed.location);

      if (found) {
        locationVerified = true;
        place = found;
      } else if (found === null) {
        // Pas un lieu connu (ex: "pas cher", "blablabla")
        locationVerified = false;
        location = null;
      }
      // found === undefined : API indisponible → on garde le candidat non vérifié
    }

    const result: SearchResult = {
      query: query.trim(),
      type: determineType(parsed.category, parsed.intent, location),
      category: parsed.category,
      intent: parsed.intent,
      location,
      location_verified: locationVerified,
      place,
      relation: parsed.relation
    };

    return new Response(
      JSON.stringify(result),
      {
        status: 200,
        headers: {
          ...corsHeaders,
          "Content-Type": "application/json"
        }
      }
    );
  } catch {
    return new Response(
      JSON.stringify({
        error: "Requête invalide."
      }),
      {
        status: 400,
        headers: {
          ...corsHeaders,
          "Content-Type": "application/json"
        }
      }
    );
  }
});