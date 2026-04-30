import { apiFetch, apiPost, apiPut } from './client';
import type { MasterProfile } from '@/lib/types/master-profile';

interface MasterProfileResponse {
  request_id: string;
  data: MasterProfile;
}

interface MasterProfileImportResponse {
  message: string;
  request_id: string;
  data: MasterProfile;
}

export async function fetchMasterProfile(): Promise<MasterProfile | null> {
  const res = await apiFetch('/master-profile');
  if (res.status === 404) {
    return null;
  }
  if (!res.ok) {
    throw new Error(`Failed to load master profile (status ${res.status}).`);
  }
  const payload = (await res.json()) as MasterProfileResponse;
  return payload.data;
}

export async function updateMasterProfile(profile: MasterProfile): Promise<MasterProfile> {
  const res = await apiPut('/master-profile', profile);
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Failed to save master profile (status ${res.status}): ${text}`);
  }
  const payload = (await res.json()) as MasterProfileResponse;
  return payload.data;
}

export async function importCvToMasterProfile(resumeId: string): Promise<MasterProfile> {
  const res = await apiPost('/master-profile/import', { resume_id: resumeId });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Failed to import CV (status ${res.status}): ${text}`);
  }
  const payload = (await res.json()) as MasterProfileImportResponse;
  return payload.data;
}
