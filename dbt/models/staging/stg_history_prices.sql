-- Cleaned price changes from the monthly history files.
-- One row = one price change at one station for one fuel type.
-- Covers all of NSW: the Greater Sydney filter happens in reporting.

with source as (

    select * from {{ source('raw', 'fuel_price_history') }}

),

renamed as (

    -- Consistent snake_case names; trim stray spaces; standardise case
    select
        trim(ServiceStationName)   as station_name,
        trim(Address)              as address,
        upper(trim(Suburb))        as suburb,
        trim(Postcode)             as postcode,
        trim(Brand)                as brand,
        upper(trim(FuelCode))      as fuel_code,
        PriceUpdatedDate           as price_updated_at,   -- Sydney local time
        Price                      as price_cpl,          -- cents per litre
        source_file,
        loaded_at
    from source

),

deduplicated as (

    -- Remove exact duplicate rows (18 in the 24 in-scope files)
    select distinct * from renamed

),

final as (

    select
        -- History files have no station code, so build one from name + address
        to_hex(md5(concat(lower(station_name), '|', lower(address)))) as station_key,
        station_name,
        address,
        suburb,
        postcode,
        brand,
        fuel_code,
        price_updated_at,
        date(price_updated_at) as price_date,
        price_cpl,

        -- Flags (rows are kept, never deleted)
        fuel_code in ('E10', 'U91', 'P95', 'P98', 'DL', 'PDL')
            and price_cpl < 100        as is_outlier,   -- likely typo, e.g. 55.9 for 155.9
        fuel_code != 'EV'              as is_fuel,      -- EV is charging, not fuel

        source_file,
        loaded_at
    from deduplicated

)

select * from final
