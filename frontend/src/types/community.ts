export interface CommunityBoardCard {
  id: number;
  column_id: string;
  name: string;
  stage: string;
  owner: string;
  due_date?: string;
  priority: string;
  status: string;
  comments?: string | null;
  link?: string | null;
}
