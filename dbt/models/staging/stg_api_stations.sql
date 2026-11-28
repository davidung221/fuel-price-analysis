-- Stations from the daily API snapshots, cleaned.
-- One row = one station, with its details from the latest snapshot it appeared in.
-- Covers all of NSW: the Greater Sydney filter happens in reporting.

with source as (

    select * from {{ source('raw', 'api_stations') }}

),

ranked as (

    select
        *,
        -- 1 = this station's most recent snapshot
        row_number() over (partition by code order by snapshot_date desc) as recency_rank,
        min(snapshot_date) over (partition by code) as first_seen_snapshot,
        max(snapshot_date) over (partition by code) as last_seen_snapshot
    from source

),

latest as (

    -- Keep only each station's most recent details
    select * from ranked
    where recency_rank = 1

),

final as (

    select
        trim(code)                 as station_code,
        trim(stationid)            as station_id,
        trim(brandid)              as brand_id,
        trim(brand)                as brand,
        trim(name)                 as station_name,
        trim(address)              as address,

        -- Take suburb and postcode from "307-313 Ocean Beach Road, UMINA BEACH NSW 2257"
        upper(trim(regexp_extract(address,
             r'(?i),\s*([^,]+?)(?:\s+(?:NSW|ACT))?\s+\d{4}\s*$')))             as suburb,
        regexp_extract(address, r'(\d{4})\s*$')                                 as postcode,

        isAdBlueAvailable          as is_adblue_available,
        first_seen_snapshot,
        last_seen_snapshot,
        -- False if the station has dropped out of the API (e.g. closed)
        last_seen_snapshot = (select max(snapshot_date) from source) as is_active

        -- latitude and longitude are left out (kept in raw if ever needed)
    from latest

)

select * from final
