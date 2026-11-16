/** Stage release compatibility preset. Source geometry and collision stay intact.
 * Shorter visible/reflection ranges are an explicit presentation tradeoff, not
 * proof that the original full skyline/overview budget has passed.
 */
export const COMPATIBLE_CITY_RANGE={visible:760,reflection:600,streetShadow:520,overviewShadow:600,retentionMargin:320,fogStart:280,fogEnd:620} as const;
