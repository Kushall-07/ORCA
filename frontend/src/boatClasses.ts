// Boat class = user-declared UX context (see ../backend app.models.vessel),
// same "echoed to /query, never changes reasoning" posture as ../stakeholders.
// Used only to annotate the ranked PFZ zone list with an approximate
// operating-range hint (QueryResponse.pfz_zones.zones[].within_safe_range).
import type { StringKey } from "./i18n/strings";

export type BoatClassId =
  | "traditional_nonmotorized"
  | "small_motorized"
  | "medium_mechanized"
  | "large_mechanized";

export interface BoatClassOption {
  id: BoatClassId;
  labelKey: StringKey;
}

export const BOAT_CLASSES: BoatClassOption[] = [
  { id: "traditional_nonmotorized", labelKey: "boatClass.traditionalNonmotorized" },
  { id: "small_motorized", labelKey: "boatClass.smallMotorized" },
  { id: "medium_mechanized", labelKey: "boatClass.mediumMechanized" },
  { id: "large_mechanized", labelKey: "boatClass.largeMechanized" },
];
