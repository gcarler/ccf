export interface AgendaEvent {
  id: number;
  title: string;
  description?: string | null;
  start_at: string;
  end_at?: string | null;
  location?: string | null;
  is_all_day: boolean;
}

export interface AgendaFormState {
  title: string;
  description: string;
  start_at: string;
  end_at: string;
  location: string;
}
