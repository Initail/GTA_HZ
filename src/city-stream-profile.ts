/** Historical compatibility preset, retained for explicit probes/regressions.
 * The playable world now requests full original coverage at every quality.
 * Do not reapply this short range as an implicit low-quality setting.
 */
export const COMPATIBLE_CITY_RANGE={visible:760,reflection:600,streetShadow:520,overviewShadow:600,retentionMargin:320} as const;
