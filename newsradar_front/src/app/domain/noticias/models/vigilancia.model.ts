export interface TopicItem {
  group_id: string;
  display_name: string;
  term_count: number;
}

export interface SubscribeRequest {
  email: string;
  name: string;
  query_groups: string[];
}

export interface SubscribeResponse {
  status: string;
  email: string;
  subscribed_groups: string[];
}

export interface Subscription {
  id: string;
  email: string;
  query_groups: string[];
  active: boolean;
}

export interface SubscriptionDelivery {
  id: string;
  subscription_id: string;
  execution_id: string | null;
  status: string;
  subject: string | null;
  delivered_at: string | null;
  content: Record<string, unknown>;
}
