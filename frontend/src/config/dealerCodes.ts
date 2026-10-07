/**
 * Seeded dealer_master rows (backend/src/app/repository/schema.sql).
 * There is no dealer-facing UI or dealer-listing endpoint, so this is a
 * plain reference list for whoever is typing a dealer code into an
 * activation or CSR-override form.
 *
 * Config layer.
 */

export interface KnownDealerCode {
  code: string;
  name: string;
}

export const KNOWN_DEALER_CODES: ReadonlyArray<KnownDealerCode> = [
  { code: "DLR-BLR-001", name: "Bengaluru Central Retail" },
  { code: "DLR-DEL-002", name: "Delhi Connaught Place Outlet" },
  { code: "DLR-MUM-003", name: "Mumbai Andheri Franchise" },
  { code: "DLR-CHN-004", name: "Chennai T Nagar Store" },
  { code: "DLR-HYD-005", name: "Hyderabad Gachibowli Kiosk" },
];
