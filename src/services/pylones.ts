import { supabase } from './supabase';

export async function chargerPylonesZone<T>(lat: number, lng: number, rayonKm: number, signal?: AbortSignal): Promise<T[]>
{
    let dLat: number;
    let dLng: number;
    let reponse: { data: unknown; error: { message: string } | null };

    dLat = rayonKm / 111;
    dLng = rayonKm / (111 * Math.cos((lat * Math.PI) / 180));
    reponse = await supabase
        .rpc('pylones_bbox', {
            min_lat: lat - dLat,
            min_lng: lng - dLng,
            max_lat: lat + dLat,
            max_lng: lng + dLng
        })
        .abortSignal(signal ?? new AbortController().signal);
    if (reponse.error)
    {
        if (signal && signal.aborted)
        {
            throw(new DOMException('Requête annulée', 'AbortError'));
        }
        throw(new Error(reponse.error.message));
    }
    return((reponse.data ?? []) as T[]);
}
