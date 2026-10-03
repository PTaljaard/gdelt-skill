DECLARE start_date DATE DEFAULT '2026-09-20';
DECLARE end_date DATE DEFAULT '2026-09-30';

SELECT
  GKGRECORDID,
  DATE(CAST(Date AS STRING)) AS EventDate,
  SourceCommonName,
  DocumentIdentifier,
  V2Themes,
  V2Locations,
  V2Persons,
  V2Organizations,
  V2Tone,
  SharingImage,
  SocialImageEmbeds,
  TranslationInfo
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONDATE BETWEEN start_date AND end_date
  AND (V2Themes LIKE '%SOUTH_AFRICA%' 
       OR V2Locations LIKE '%SOUTH_AFRICA%'
       OR LOWER(DocumentIdentifier) LIKE '%south%africa%')
  AND (
    LOWER(V2Themes) LIKE '%rural_safety%' 
    OR LOWER(V2Themes) LIKE '%crime_violence%'
    OR LOWER(V2Themes) LIKE '%ethnic_conflict%'
    OR LOWER(DocumentIdentifier) LIKE '%farm%murder%'
    OR LOWER(DocumentIdentifier) LIKE '%white%cross%'
    OR LOWER(DocumentIdentifier) LIKE '%lex%libertas%'
    OR LOWER(DocumentIdentifier) LIKE '%roets%'
  )
ORDER BY EventDate DESC
LIMIT 500;