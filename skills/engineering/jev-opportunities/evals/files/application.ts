// Synthetic audit fixture. External operations are injected; this file makes no calls.
export interface TextModel {
  generate(prompt: string): Promise<string>;
}

export interface SearchIndex {
  search(query: string): Promise<readonly Passage[]>;
}

export interface Passage {
  readonly id: string;
  readonly text: string;
}

export type Queue = 'billing' | 'technical' | 'sales' | 'review';

export async function routeTicket(model: TextModel, message: string): Promise<Queue> {
  const answer = await model.generate(
    `Classify this ticket as billing, technical, sales, or review. Return only the label.\n${message}`,
  );
  switch (answer.trim()) {
    case 'billing': return 'billing';
    case 'technical': return 'technical';
    case 'sales': return 'sales';
    default: return 'review';
  }
}

export async function draftAnswer(
  model: TextModel,
  index: SearchIndex,
  query: string,
): Promise<string> {
  const candidates = await index.search(query);
  return model.generate(
    `Answer with citations from these passages.\n${JSON.stringify({ query, candidates })}`,
  );
}

export function canReadTicket(actorTenant: string, ticketTenant: string): boolean {
  return actorTenant === ticketTenant;
}

export function lineTotalCents(priceCents: number, quantity: number): number {
  if (!Number.isSafeInteger(priceCents) || !Number.isSafeInteger(quantity)
      || priceCents < 0 || quantity < 0 || !Number.isSafeInteger(priceCents * quantity)) {
    throw new RangeError('Expected non-negative safe integer cents and quantity');
  }
  return priceCents * quantity;
}
