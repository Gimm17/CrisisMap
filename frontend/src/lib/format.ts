const numberFormatter = new Intl.NumberFormat("en-US");
const utcDateTimeFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "UTC",
  timeZoneName: "short"
});

export function formatNumber(value: number): string {
  return numberFormatter.format(value);
}

export function formatDateTime(value: string | number | Date): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--";
  return utcDateTimeFormatter.format(date);
}
