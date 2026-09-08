"""QuickBooks API client wrapper."""

from typing import Any, Optional

from intuitlib.client import AuthClient
from quickbooks import QuickBooks
from quickbooks.objects.account import Account
from quickbooks.objects.bill import Bill
from quickbooks.objects.billpayment import BillPayment
from quickbooks.objects.customer import Customer
from quickbooks.objects.employee import Employee
from quickbooks.objects.invoice import Invoice
from quickbooks.objects.item import Item
from quickbooks.objects.payment import Payment
from quickbooks.objects.vendor import Vendor

from quickbooks_sync.exceptions import (
    APIError,
    OAuthError,
    RateLimitError,
    TokenExpiredError,
)
from quickbooks_sync.settings import qbs_settings
from quickbooks_sync.utils import calculate_token_expiry, mask_sensitive_data

# Entity mapping from string name to QuickBooks object class
ENTITY_MAP = {
    "Account": Account,
    "Customer": Customer,
    "Vendor": Vendor,
    "Employee": Employee,
    "Invoice": Invoice,
    "Bill": Bill,
    "Payment": Payment,
    "BillPayment": BillPayment,
    "Item": Item,
}


class QuickBooksClient:
    """
    Wrapper around python-quickbooks for QuickBooks Online API.

    Handles OAuth authentication, token management, and API calls.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        realm_id: Optional[str] = None,
        environment: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ):
        """
        Initialize the QuickBooks client.

        Args:
            client_id: QuickBooks OAuth client ID
            client_secret: QuickBooks OAuth client secret
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            realm_id: QuickBooks company/realm ID
            environment: 'sandbox' or 'production'
            redirect_uri: OAuth redirect URI
        """
        self.client_id = client_id or qbs_settings.CLIENT_ID
        self.client_secret = client_secret or qbs_settings.CLIENT_SECRET
        self.access_token = access_token or qbs_settings.ACCESS_TOKEN
        self.refresh_token = refresh_token or qbs_settings.REFRESH_TOKEN
        self.realm_id = realm_id or qbs_settings.REALM_ID
        self.environment = environment or qbs_settings.ENVIRONMENT
        self.redirect_uri = redirect_uri or qbs_settings.REDIRECT_URI

        self._auth_client: Optional[AuthClient] = None
        self._qb_client: Optional[QuickBooks] = None

    @property
    def auth_client(self) -> AuthClient:
        """Get or create the AuthClient."""
        if self._auth_client is None:
            self._auth_client = AuthClient(
                client_id=self.client_id,
                client_secret=self.client_secret,
                access_token=self.access_token,
                environment=self.environment,
                redirect_uri=self.redirect_uri,
            )
        return self._auth_client

    @property
    def qb_client(self) -> QuickBooks:
        """Get or create the QuickBooks client."""
        if self._qb_client is None:
            self._qb_client = QuickBooks(
                auth_client=self.auth_client,
                refresh_token=self.refresh_token,
                company_id=self.realm_id,
            )
        return self._qb_client

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Get the OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        return self.auth_client.get_authorization_url(
            scope=["com.intuit.quickbooks.accounting"],
            state=state,
        )

    def exchange_code(self, authorization_response_url: str) -> dict:
        """
        Exchange authorization code for tokens.

        Args:
            authorization_response_url: The full callback URL with authorization code

        Returns:
            Dictionary with token information
        """
        try:
            token_response = self.auth_client.create_token(authorization_response_url)
            token_data = token_response.get("access_token")
            self.access_token = token_data
            self.refresh_token = token_response.get("refresh_token", self.refresh_token)

            return {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "token_type": token_response.get("token_type"),
                "expires_in": token_response.get("expires_in"),
                "x_refresh_token_expires_in": token_response.get(
                    "x_refresh_token_expires_in"
                ),
                "realm_id": self.realm_id,
            }
        except Exception as e:
            raise OAuthError(f"Failed to exchange authorization code: {str(e)}")

    def refresh_access_token(self) -> dict:
        """
        Refresh the access token using the refresh token.

        Returns:
            Dictionary with new token information
        """
        try:
            token_response = self.auth_client.refresh()
            self.access_token = token_response.get("access_token")
            self.refresh_token = token_response.get("refresh_token", self.refresh_token)

            return {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "token_type": token_response.get("token_type"),
                "expires_in": token_response.get("expires_in"),
                "x_refresh_token_expires_in": token_response.get(
                    "x_refresh_token_expires_in"
                ),
            }
        except Exception as e:
            raise OAuthError(f"Failed to refresh access token: {str(e)}")

    def get_entity(
        self, entity_type: str, entity_id: str
    ) -> Any:
        """
        Get a single entity from QuickBooks.

        Args:
            entity_type: Entity type (e.g., 'Customer', 'Invoice')
            entity_id: Entity ID

        Returns:
            QuickBooks entity object
        """
        entity_class = ENTITY_MAP.get(entity_type)
        if not entity_class:
            raise APIError(f"Unknown entity type: {entity_type}")

        try:
            return entity_class.get(entity_id, qb=self.qb_client)
        except Exception as e:
            if "401" in str(e):
                raise TokenExpiredError()
            raise APIError(f"Failed to get {entity_type}: {str(e)}")

    def query_entities(
        self,
        entity_type: str,
        query: Optional[str] = None,
        max_results: int = 1000,
        start_position: int = 1,
    ) -> list:
        """
        Query entities from QuickBooks.

        Args:
            entity_type: Entity type to query
            query: SQL-like query string (optional)
            max_results: Maximum number of results
            start_position: Starting position for pagination

        Returns:
            List of QuickBooks entity objects
        """
        entity_class = ENTITY_MAP.get(entity_type)
        if not entity_class:
            raise APIError(f"Unknown entity type: {entity_type}")

        try:
            if query is None:
                query = f"SELECT * FROM {entity_type}"

            # Add pagination
            query += f" ORDERBY Id STARTPOSITION {start_position} MAXRESULTS {max_results}"

            return entity_class.query(query, qb=self.qb_client)
        except Exception as e:
            if "401" in str(e):
                raise TokenExpiredError()
            if "429" in str(e):
                raise RateLimitError()
            raise APIError(f"Failed to query {entity_type}: {str(e)}")

    def create_entity(self, entity_type: str, entity_data: dict) -> Any:
        """
        Create a new entity in QuickBooks.

        Args:
            entity_type: Entity type to create
            entity_data: Dictionary with entity data

        Returns:
            Created QuickBooks entity object
        """
        entity_class = ENTITY_MAP.get(entity_type)
        if not entity_class:
            raise APIError(f"Unknown entity type: {entity_type}")

        try:
            entity = entity_class()
            for key, value in entity_data.items():
                setattr(entity, key, value)

            entity.save(qb=self.qb_client)
            return entity
        except Exception as e:
            if "401" in str(e):
                raise TokenExpiredError()
            if "429" in str(e):
                raise RateLimitError()
            raise APIError(f"Failed to create {entity_type}: {str(e)}")

    def update_entity(
        self, entity_type: str, entity_id: str, entity_data: dict
    ) -> Any:
        """
        Update an existing entity in QuickBooks.

        Args:
            entity_type: Entity type to update
            entity_id: Entity ID to update
            entity_data: Dictionary with updated data

        Returns:
            Updated QuickBooks entity object
        """
        entity_class = ENTITY_MAP.get(entity_type)
        if not entity_class:
            raise APIError(f"Unknown entity type: {entity_type}")

        try:
            entity = entity_class.get(entity_id, qb=self.qb_client)
            for key, value in entity_data.items():
                setattr(entity, key, value)

            entity.save(qb=self.qb_client)
            return entity
        except Exception as e:
            if "401" in str(e):
                raise TokenExpiredError()
            if "429" in str(e):
                raise RateLimitError()
            raise APIError(f"Failed to update {entity_type}: {str(e)}")

    def delete_entity(self, entity_type: str, entity_id: str) -> bool:
        """
        Delete an entity from QuickBooks.

        Note: Not all entities support deletion in QuickBooks.
        This method uses void for transaction entities.

        Args:
            entity_type: Entity type to delete
            entity_id: Entity ID to delete

        Returns:
            True if successful
        """
        entity_class = ENTITY_MAP.get(entity_type)
        if not entity_class:
            raise APIError(f"Unknown entity type: {entity_type}")

        try:
            entity = entity_class.get(entity_id, qb=self.qb_client)

            # Check if entity has delete method (some entities support it)
            if hasattr(entity, "delete"):
                entity.delete(qb=self.qb_client)
            else:
                # For entities without delete, we just mark as inactive
                # or use a void operation for transaction entities
                raise APIError(
                    f"Entity type {entity_type} does not support direct deletion. "
                    "Use void operation for transaction entities."
                )
            return True
        except APIError:
            raise
        except Exception as e:
            if "401" in str(e):
                raise TokenExpiredError()
            if "429" in str(e):
                raise RateLimitError()
            raise APIError(f"Failed to delete {entity_type}: {str(e)}")

    def get_company_info(self) -> Any:
        """
        Get company information.

        Returns:
            CompanyInfo object
        """
        try:
            from quickbooks.objects.companyinfo import CompanyInfo

            return CompanyInfo.get("1", qb=self.qb_client)
        except Exception as e:
            if "401" in str(e):
                raise TokenExpiredError()
            raise APIError(f"Failed to get company info: {str(e)}")

    def get_change_data_capture(self, entity_types: list[str]) -> list:
        """
        Get change data capture for specified entity types.

        Args:
            entity_types: List of entity types to check for changes

        Returns:
            List of changed entities
        """
        try:
            from quickbooks.objects.changeDataCapture import ChangeDataCapture

            entity_list = ",".join(entity_types)
            query = f"SELECT * FROM {entity_list}"
            return ChangeDataCapture.query(query, qb=self.qb_client)
        except Exception as e:
            if "401" in str(e):
                raise TokenExpiredError()
            raise APIError(f"Failed to get change data capture: {str(e)}")

    def to_dict(self) -> dict:
        """Convert client to dictionary (excluding sensitive data)."""
        return {
            "client_id": mask_sensitive_data(self.client_id),
            "realm_id": self.realm_id,
            "environment": self.environment,
            "access_token": mask_sensitive_data(self.access_token),
            "refresh_token": mask_sensitive_data(self.refresh_token),
        }
