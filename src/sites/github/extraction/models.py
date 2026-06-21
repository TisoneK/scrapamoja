"""
GitHub data models extending base framework models.

This module defines data models for GitHub-specific data structures,
extending the existing framework models where appropriate.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum


class IssueState(Enum):
    """GitHub issue states."""
    OPEN = "open"
    CLOSED = "closed"
    LOCKED = "locked"


class RepositoryVisibility(Enum):
    """Repository visibility levels."""
    PUBLIC = "public"
    PRIVATE = "private"
    INTERNAL = "internal"


@dataclass
class GitHubRepository:
    """GitHub repository data model."""
    
    # Basic Information
    name: str
    full_name: str
    description: str = ""
    url: str = ""
    
    # Statistics
    stars: int = 0
    forks: int = 0
    issues: int = 0
    watchers: int = 0
    
    # Metadata
    language: str = ""
    license: Optional[str] = None
    topics: List[str] = field(default_factory=list)
    contributors: int = 0
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    pushed_at: Optional[datetime] = None
    
    # Visibility and Status
    visibility: RepositoryVisibility = RepositoryVisibility.PUBLIC
    is_archived: bool = False
    is_disabled: bool = False
    
    # Owner Information
    owner_login: str = ""
    owner_type: str = ""
    
    # Extraction Metadata
    extracted_at: datetime = field(default_factory=datetime.now)
    extraction_source: str = "github_scraper"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "full_name": self.full_name,
            "description": self.description,
            "url": self.url,
            "stars": self.stars,
            "forks": self.forks,
            "issues": self.issues,
            "watchers": self.watchers,
            "language": self.language,
            "license": self.license,
            "topics": self.topics,
            "contributors": self.contributors,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "pushed_at": self.pushed_at.isoformat() if self.pushed_at else None,
            "visibility": self.visibility.value,
            "is_archived": self.is_archived,
            "is_disabled": self.is_disabled,
            "owner_login": self.owner_login,
            "owner_type": self.owner_type,
            "extracted_at": self.extracted_at.isoformat(),
            "extraction_source": self.extraction_source
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GitHubRepository":
        """Create instance from dictionary."""
        # Handle timestamps
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        
        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])
        
        pushed_at = None
        if data.get("pushed_at"):
            pushed_at = datetime.fromisoformat(data["pushed_at"])
        
        extracted_at = datetime.now()
        if data.get("extracted_at"):
            extracted_at = datetime.fromisoformat(data["extracted_at"])
        
        # Handle visibility
        visibility = RepositoryVisibility.PUBLIC
        if data.get("visibility"):
            try:
                visibility = RepositoryVisibility(data["visibility"])
            except ValueError:
                visibility = RepositoryVisibility.PUBLIC
        
        return cls(
            name=data.get("name", ""),
            full_name=data.get("full_name", ""),
            description=data.get("description", ""),
            url=data.get("url", ""),
            stars=data.get("stars", 0),
            forks=data.get("forks", 0),
            issues=data.get("issues", 0),
            watchers=data.get("watchers", 0),
            language=data.get("language", ""),
            license=data.get("license"),
            topics=data.get("topics", []),
            contributors=data.get("contributors", 0),
            created_at=created_at,
            updated_at=updated_at,
            pushed_at=pushed_at,
            visibility=visibility,
            is_archived=data.get("is_archived", False),
            is_disabled=data.get("is_disabled", False),
            owner_login=data.get("owner_login", ""),
            owner_type=data.get("owner_type", ""),
            extracted_at=extracted_at,
            extraction_source=data.get("extraction_source", "github_scraper")
        )


@dataclass
class GitHubUser:
    """GitHub user data model."""
    
    # Basic Information
    login: str
    name: str = ""
    bio: str = ""
    url: str = ""
    avatar_url: str = ""
    
    # Statistics
    followers: int = 0
    following: int = 0
    public_repos: int = 0
    
    # Location and Contact
    location: str = ""
    email: str = ""
    blog: str = ""
    company: str = ""
    
    # Status
    hireable: bool = False
    site_admin: bool = False
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Extraction Metadata
    extracted_at: datetime = field(default_factory=datetime.now)
    extraction_source: str = "github_scraper"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "login": self.login,
            "name": self.name,
            "bio": self.bio,
            "url": self.url,
            "avatar_url": self.avatar_url,
            "followers": self.followers,
            "following": self.following,
            "public_repos": self.public_repos,
            "location": self.location,
            "email": self.email,
            "blog": self.blog,
            "company": self.company,
            "hireable": self.hireable,
            "site_admin": self.site_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "extracted_at": self.extracted_at.isoformat(),
            "extraction_source": self.extraction_source
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GitHubUser":
        """Create instance from dictionary."""
        # Handle timestamps
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        
        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])
        
        extracted_at = datetime.now()
        if data.get("extracted_at"):
            extracted_at = datetime.fromisoformat(data["extracted_at"])
        
        return cls(
            login=data.get("login", ""),
            name=data.get("name", ""),
            bio=data.get("bio", ""),
            url=data.get("url", ""),
            avatar_url=data.get("avatar_url", ""),
            followers=data.get("followers", 0),
            following=data.get("following", 0),
            public_repos=data.get("public_repos", 0),
            location=data.get("location", ""),
            email=data.get("email", ""),
            blog=data.get("blog", ""),
            company=data.get("company", ""),
            hireable=data.get("hireable", False),
            site_admin=data.get("site_admin", False),
            created_at=created_at,
            updated_at=updated_at,
            extracted_at=extracted_at,
            extraction_source=data.get("extraction_source", "github_scraper")
        )


@dataclass
class GitHubIssue:
    """GitHub issue data model."""
    
    # Basic Information
    id: int
    number: int
    title: str
    body: str = ""
    url: str = ""
    
    # Status and State
    state: IssueState = IssueState.OPEN
    locked: bool = False
    
    # Author and Assignee
    author_login: str = ""
    author_association: str = ""
    assignee_login: str = ""
    assignees: List[str] = field(default_factory=list)
    
    # Labels and Milestone
    labels: List[str] = field(default_factory=list)
    milestone: Optional[str] = None
    
    # Comments and Reactions
    comments: int = 0
    reactions: Dict[str, int] = field(default_factory=dict)
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    
    # Repository Information
    repository_name: str = ""
    repository_url: str = ""
    
    # Extraction Metadata
    extracted_at: datetime = field(default_factory=datetime.now)
    extraction_source: str = "github_scraper"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "number": self.number,
            "title": self.title,
            "body": self.body,
            "url": self.url,
            "state": self.state.value,
            "locked": self.locked,
            "author_login": self.author_login,
            "author_association": self.author_association,
            "assignee_login": self.assignee_login,
            "assignees": self.assignees,
            "labels": self.labels,
            "milestone": self.milestone,
            "comments": self.comments,
            "reactions": self.reactions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "repository_name": self.repository_name,
            "repository_url": self.repository_url,
            "extracted_at": self.extracted_at.isoformat(),
            "extraction_source": self.extraction_source
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GitHubIssue":
        """Create instance from dictionary."""
        # Handle timestamps
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        
        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])
        
        closed_at = None
        if data.get("closed_at"):
            closed_at = datetime.fromisoformat(data["closed_at"])
        
        extracted_at = datetime.now()
        if data.get("extracted_at"):
            extracted_at = datetime.fromisoformat(data["extracted_at"])
        
        # Handle state
        state = IssueState.OPEN
        if data.get("state"):
            try:
                state = IssueState(data["state"])
            except ValueError:
                state = IssueState.OPEN
        
        return cls(
            id=data.get("id", 0),
            number=data.get("number", 0),
            title=data.get("title", ""),
            body=data.get("body", ""),
            url=data.get("url", ""),
            state=state,
            locked=data.get("locked", False),
            author_login=data.get("author_login", ""),
            author_association=data.get("author_association", ""),
            assignee_login=data.get("assignee_login", ""),
            assignees=data.get("assignees", []),
            labels=data.get("labels", []),
            milestone=data.get("milestone"),
            comments=data.get("comments", 0),
            reactions=data.get("reactions", {}),
            created_at=created_at,
            updated_at=updated_at,
            closed_at=closed_at,
            repository_name=data.get("repository_name", ""),
            repository_url=data.get("repository_url", ""),
            extracted_at=extracted_at,
            extraction_source=data.get("extraction_source", "github_scraper")
        )


@dataclass
class GitHubSearchResult:
    """GitHub search result data model."""
    
    # Search Information
    query: str
    search_type: str = "repositories"
    total_results: int = 0
    page: int = 1
    per_page: int = 20
    
    # Results
    repositories: List[GitHubRepository] = field(default_factory=list)
    users: List[GitHubUser] = field(default_factory=list)
    issues: List[GitHubIssue] = field(default_factory=list)
    
    # Search Metadata
    search_url: str = ""
    search_time: float = 0.0
    
    # Extraction Metadata
    extracted_at: datetime = field(default_factory=datetime.now)
    extraction_source: str = "github_scraper"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "query": self.query,
            "search_type": self.search_type,
            "total_results": self.total_results,
            "page": self.page,
            "per_page": self.per_page,
            "repositories": [repo.to_dict() for repo in self.repositories],
            "users": [user.to_dict() for user in self.users],
            "issues": [issue.to_dict() for issue in self.issues],
            "search_url": self.search_url,
            "search_time": self.search_time,
            "extracted_at": self.extracted_at.isoformat(),
            "extraction_source": self.extraction_source
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GitHubSearchResult":
        """Create instance from dictionary."""
        extracted_at = datetime.now()
        if data.get("extracted_at"):
            extracted_at = datetime.fromisoformat(data["extracted_at"])
        
        # Convert nested objects
        repositories = []
        for repo_data in data.get("repositories", []):
            repositories.append(GitHubRepository.from_dict(repo_data))
        
        users = []
        for user_data in data.get("users", []):
            users.append(GitHubUser.from_dict(user_data))
        
        issues = []
        for issue_data in data.get("issues", []):
            issues.append(GitHubIssue.from_dict(issue_data))
        
        return cls(
            query=data.get("query", ""),
            search_type=data.get("search_type", "repositories"),
            total_results=data.get("total_results", 0),
            page=data.get("page", 1),
            per_page=data.get("per_page", 20),
            repositories=repositories,
            users=users,
            issues=issues,
            search_url=data.get("search_url", ""),
            search_time=data.get("search_time", 0.0),
            extracted_at=extracted_at,
            extraction_source=data.get("extraction_source", "github_scraper")
        )


@dataclass
class GitHubExtractionResult:
    """Generic GitHub extraction result wrapper."""
    
    # Result Information
    success: bool
    data_type: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    # Performance Metrics
    extraction_time: float = 0.0
    elements_processed: int = 0
    
    # Metadata
    extracted_at: datetime = field(default_factory=datetime.now)
    extraction_source: str = "github_scraper"
    template_version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "data_type": self.data_type,
            "data": self.data,
            "error": self.error,
            "extraction_time": self.extraction_time,
            "elements_processed": self.elements_processed,
            "extracted_at": self.extracted_at.isoformat(),
            "extraction_source": self.extraction_source,
            "template_version": self.template_version
        }
    
    @classmethod
    def success_result(cls, data_type: str, data: Dict[str, Any], extraction_time: float = 0.0, elements_processed: int = 0) -> "GitHubExtractionResult":
        """Create a successful extraction result."""
        return cls(
            success=True,
            data_type=data_type,
            data=data,
            extraction_time=extraction_time,
            elements_processed=elements_processed
        )
    
    @classmethod
    def error_result(cls, data_type: str, error: str, extraction_time: float = 0.0) -> "GitHubExtractionResult":
        """Create an error extraction result."""
        return cls(
            success=False,
            data_type=data_type,
            error=error,
            extraction_time=extraction_time
        )
