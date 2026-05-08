from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


def _to_camel(snake: str) -> str:
    if "_" not in snake:
        return snake
    head, *tail = snake.split("_")
    return head + "".join(p.title() for p in tail)


_camel = ConfigDict(populate_by_name=True, alias_generator=_to_camel)


class ApiErrorException(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class ClubAddress(BaseModel):
    model_config = _camel
    line: str | None = None
    city: str | None = None
    region: str | None = None
    postal_code: str | None = Field(default=None, alias="postalCode")
    latitude: float | None = None
    longitude: float | None = None


class ContactInfo(BaseModel):
    model_config = _camel
    phone_no: str | None = Field(default=None, alias="phoneNo")
    email: str | None = None
    www: str | None = None
    facebook_profile: str | None = Field(default=None, alias="facebookProfile")
    instagram_profile: str | None = Field(default=None, alias="instagramProfile")
    tik_tok_profile: str | None = Field(default=None, alias="tikTokProfile")
    twitter_profile: str | None = Field(default=None, alias="twitterProfile")


class OpenDayHours(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    from_: str = Field(alias="from")
    to: str


class OpenHours(BaseModel):
    monday: OpenDayHours
    tuesday: OpenDayHours
    wednesday: OpenDayHours
    thursday: OpenDayHours
    friday: OpenDayHours
    saturday: OpenDayHours
    sunday: OpenDayHours


class Club(BaseModel):
    model_config = _camel
    id: str
    name: str
    address: ClubAddress
    contact_info: ContactInfo = Field(alias="contactInfo")
    logo_url: str | None = Field(default=None, alias="logoUrl")
    banner_url: str | None = Field(default=None, alias="bannerUrl")
    price_min: float | None = Field(default=None, alias="priceMin")
    price_max: float | None = Field(default=None, alias="priceMax")
    locations_count: int = Field(alias="locationsCount")
    open_hours: OpenHours = Field(alias="openHours")
    is_smart_tennis_partner: bool = Field(alias="isSmartTennisPartner")
    multi_sport_discount: float | None = Field(default=None, alias="multiSportDiscount")
    medicover_discount: float | None = Field(default=None, alias="medicoverDiscount")


class Location(BaseModel):
    """A bookable court within a club. Returned in the `locations` field of /Clubs/{id}."""

    model_config = _camel
    id: str
    name: str
    short_name: str | None = Field(default=None, alias="shortName")
    has_light: bool = Field(default=False, alias="hasLight")
    is_enabled: bool = Field(default=True, alias="isEnabled")
    tags: str | None = None
    sort_number: int = Field(default=0, alias="sortNumber")
    type: int = 0
    group_name: str | None = Field(default=None, alias="groupName")


class TechnicalGroup(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str
    service_url: str = Field(alias="serviceUrl")
    name: str


class PlayerProfile(BaseModel):
    model_config = _camel
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    phone_number: str | None = Field(default=None, alias="phoneNumber")
    email: str
    id: str
    preferred_region_id: str | None = Field(default=None, alias="preferredRegionId")
    year_of_birth: int | None = Field(default=None, alias="yearOfBirth")


class ClubPlayer(BaseModel):
    """Player record inside a specific club — `id` is the bookerId used in POST /bookings."""

    model_config = _camel
    id: str
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    phone_number: str | None = Field(default=None, alias="phoneNumber")
    email: str | None = None
    player_id: str = Field(alias="playerId")
    club_id: str = Field(alias="clubId")


class BookerInfo(BaseModel):
    model_config = _camel
    booker_id: str = Field(alias="bookerId")
    cached_name: str = Field(alias="cachedName")
    cached_email: str | None = Field(default=None, alias="cachedEmail")
    cached_phone: str | None = Field(default=None, alias="cachedPhone")
    type: int = 0


class BookingPayment(BaseModel):
    model_config = _camel
    id: str | None = None
    status: str
    paid_amount: float = Field(alias="paidAmount")
    payment_due: str | None = Field(default=None, alias="paymentDue")
    discount_type: str = Field(alias="discountType")
    discount_value: float = Field(alias="discountValue")
    amount_to_pay: float = Field(alias="amountToPay")
    initial_amount: float = Field(alias="initialAmount")


class Reservation(BaseModel):
    model_config = _camel
    id: str
    club_id: str = Field(alias="clubId")
    club_name: str | None = Field(default=None, alias="clubName")
    location_id: str = Field(alias="locationId")
    location_name: str | None = Field(default=None, alias="locationName")
    date: str
    start_time: str = Field(alias="startTime")
    end_time: str = Field(alias="endTime")
    price: float | None = None
    payment: BookingPayment | None = None
    booked_for: BookerInfo | None = Field(default=None, alias="bookedFor")
    cancel_until: str | None = Field(default=None, alias="cancelUntil")
    is_deleted: bool = Field(default=False, alias="isDeleted")
    created_on: str | None = Field(default=None, alias="createdOn")


class PriceCalculationRequest(BaseModel):
    model_config = _camel
    club_id: str = Field(alias="clubId")
    location_id: str = Field(alias="locationId")
    start: str
    end: str
    days: list[str]
    multi_sport_cards_used: int = Field(default=0, alias="multiSportCardsUsed")
    medicover_cards_used: int = Field(default=0, alias="medicoverCardsUsed")


class PriceForDay(BaseModel):
    model_config = _camel
    day: str
    price: float
    initial_price: float = Field(alias="initialPrice")
    checksum: str
    failed: bool
    discount: float = 0
    multi_sport_cards_used: int = Field(default=0, alias="multiSportCardsUsed")
    medicover_cards_used: int = Field(default=0, alias="medicoverCardsUsed")


class PriceCalculationResult(BaseModel):
    model_config = _camel
    club_id: str = Field(alias="clubId")
    location_id: str = Field(alias="locationId")
    start: str
    end: str
    prices: list[PriceForDay]
