export interface CharacterStats {
  diplomacy: number;
  martial: number;
  stewardship: number;
  intrigue: number;
  learning: number;
  prowess: number;
}

export interface CK3Character {
  id: string;
  name: string;
  dynasty_id: string | null;
  culture: string;
  religion: string;
  traits: string[];
  stats: CharacterStats;
  birth_date: string;
  death_date: string | null;
  is_female: boolean;
}

export interface GenerationResponse {
  message: string;
  file_path: string;
  script: string;
}
